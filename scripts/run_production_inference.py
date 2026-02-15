"""
Production inference pipeline using existing backend modules.
Converts PCAPNG → PCAP → Extract Features → Run Inference
"""

import sys
import subprocess
import json
import numpy as np
from pathlib import Path

# Add project root
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from backend.ml.inference import AnomalyPredictor
from backend.insight.generator import InsightGenerator
from scapy.all import rdpcap, wrpcap

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def convert_pcapng_to_pcap(pcapng_file: Path, pcap_file: Path):
    """Convert PCAPNG to PCAP format."""
    print(f"\n[1/3] Converting PCAPNG to PCAP...")
    
    if pcap_file.exists():
        print(f"  ✓ {pcap_file.name} already exists")
        return pcap_file
    
    print(f"  Reading: {pcapng_file.name}")
    packets = rdpcap(str(pcapng_file))
    print(f"  ✓ Read {len(packets)} packets")
    
    print(f"  Writing: {pcap_file.name}")
    wrpcap(str(pcap_file), packets)
    print(f"  ✓ Conversion complete")
    
    return pcap_file


def extract_features(pcap_file: Path, output_json: Path):
    """Extract features using Rust extractor."""
    print(f"\n[2/3] Extracting features...")
    
    if output_json.exists():
        print(f"  ✓ {output_json.name} already exists")
        with open(output_json, 'r') as f:
            data = json.load(f)
        print(f"  ✓ Loaded {len(data)} windows")
        return output_json
    
    output_json.parent.mkdir(parents=True, exist_ok=True)
    
    # Rust extractor path
    extractor_exe = ROOT / 'backend' / 'features' / 'rust_extractor' / 'target' / 'release' / 'rust_extractor.exe'
    
    if not extractor_exe.exists():
        print(f"  ✗ Rust extractor not found at {extractor_exe}")
        print(f"  Consider building: cd backend/features/rust_extractor && cargo build --release")
        sys.exit(1)
    
    print(f"  Running: {extractor_exe.name}")
    cmd = [str(extractor_exe), str(pcap_file), str(output_json)]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print(f"  ✗ Extractor failed: {result.stderr}")
            sys.exit(1)
        
        # Parse output
        for line in result.stdout.split('\n'):
            if 'windows' in line.lower():
                print(f"  ✓ {line.strip()}")
        
        return output_json
    except subprocess.TimeoutExpired:
        print(f"  ✗ Extraction timeout (>5 min)")
        sys.exit(1)


def engineer_behavioral_features(df, rolling_window=10):
    """Engineer behavioral features required by the behavioral model."""
    df = df.copy()

    if len(df) >= rolling_window:
        rolling_packets = df['packet_count'].rolling(window=rolling_window, min_periods=1).mean()
        df['pct_change_packets'] = (df['packet_count'] - rolling_packets) / (rolling_packets + 1)

        rolling_bytes_ps = df['bytes_per_sec'].rolling(window=rolling_window, min_periods=1).mean()
        df['pct_change_bytes_ps'] = (df['bytes_per_sec'] - rolling_bytes_ps) / (rolling_bytes_ps + 1)

        if 'flow_count' in df.columns:
            rolling_flows = df['flow_count'].rolling(window=rolling_window, min_periods=1).mean()
            df['pct_change_flows'] = (df['flow_count'] - rolling_flows) / (rolling_flows + 1)
    else:
        df['pct_change_packets'] = 0.0
        df['pct_change_bytes_ps'] = 0.0
        if 'flow_count' in df.columns:
            df['pct_change_flows'] = 0.0

    df['bytes_per_packet'] = df['total_bytes'] / (df['packet_count'] + 1)
    df['src_ips_per_packet'] = df['unique_src_ips'] / (df['packet_count'] + 1)
    df['dst_ips_per_packet'] = df['unique_dst_ips'] / (df['packet_count'] + 1)
    if 'flow_count' in df.columns:
        df['flow_per_packet'] = df['flow_count'] / (df['packet_count'] + 1)

    if 'max_packet_size' in df.columns and 'min_packet_size' in df.columns:
        df['packet_size_range'] = (df['max_packet_size'] - df['min_packet_size']) / (df['avg_packet_size'] + 1)

    df['protocol_diversity'] = -(
        df['tcp_ratio'] * np.log(df['tcp_ratio'] + 1e-6) +
        df['udp_ratio'] * np.log(df['udp_ratio'] + 1e-6) +
        df['icmp_ratio'] * np.log(df['icmp_ratio'] + 1e-6)
    )

    return df


def run_inference(features_json: Path, model_type='behavioral'):
    """Run inference using AnomalyPredictor."""
    print(f"\n[3/3] Running inference ({model_type} model)...")
    
    # Select model
    model_map = {
        'behavioral': 'network_anomaly_model_behavioral.pkl',
        'scale_robust': 'network_anomaly_model_scale_robust.pkl',
        'combined': 'network_anomaly_model_combined.pkl',
    }
    
    model_file = model_map.get(model_type, model_map['behavioral'])
    model_path = ROOT / 'models' / model_file
    
    if not model_path.exists():
        print(f"  ✗ Model not found: {model_path}")
        print(f"  Available models: {list(model_map.keys())}")
        sys.exit(1)
    
    print(f"  Loading model: {model_file}")
    predictor = AnomalyPredictor(model_path=str(model_path))
    
    # Load features and predict
    with open(features_json, 'r') as f:
        features = json.load(f)
    
    import pandas as pd
    df = pd.DataFrame(features)
    print(f"  ✓ Loaded {len(df)} windows for inference")

    if model_type == 'behavioral':
        df = engineer_behavioral_features(df, rolling_window=10)
    elif model_type == 'combined':
        scripts_path = ROOT / 'scripts'
        if str(scripts_path) not in sys.path:
            sys.path.insert(0, str(scripts_path))
        from data_cleanup import clean_and_engineer_features, select_features
        df_engineered = clean_and_engineer_features(df)
        df = select_features(df_engineered)
    
    print(f"  Running predictions...")
    results = predictor.predict_from_features(df)
    
    # Add metadata
    results['model_used'] = model_file
    results['n_windows'] = len(df)
    
    return results, df, predictor


def create_visualizations(df, results, output_dir: Path, name_stem: str):
    """Create a compact visualization for inference results."""
    output_dir.mkdir(parents=True, exist_ok=True)

    scores = results['scores']
    predictions = results['predictions']
    viz_scores = -scores

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    fig.suptitle(f"Inference Results - {name_stem}", fontsize=14, fontweight='bold')

    # Score timeline
    ax = axes[0, 0]
    ax.plot(viz_scores, linewidth=1.2, color='#1f77b4', alpha=0.8)
    anomaly_idx = np.where(predictions == -1)[0]
    if len(anomaly_idx) > 0:
        ax.scatter(anomaly_idx, viz_scores[anomaly_idx], color='red', s=30, label='Anomaly')
        ax.legend(loc='upper right')
    ax.set_title('Anomaly Score Timeline (higher = more anomalous)')
    ax.set_xlabel('Window Index')
    ax.set_ylabel('Anomaly Score')
    ax.grid(True, alpha=0.3)

    # Score distribution
    ax = axes[0, 1]
    normal_scores = viz_scores[predictions == 1]
    anomaly_scores = viz_scores[predictions == -1]
    ax.hist(normal_scores, bins=25, alpha=0.7, color='#2ecc71', label='Normal')
    if len(anomaly_scores) > 0:
        ax.hist(anomaly_scores, bins=15, alpha=0.7, color='#e74c3c', label='Anomaly')
    ax.set_title('Score Distribution')
    ax.set_xlabel('Anomaly Score')
    ax.set_ylabel('Count')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    # Packets vs score
    ax = axes[1, 0]
    colors = ['#e74c3c' if p == -1 else '#2ecc71' for p in predictions]
    ax.scatter(df['packet_count'], viz_scores, c=colors, alpha=0.5, s=20, edgecolors='black', linewidth=0.2)
    ax.set_title('Packet Count vs Anomaly Score')
    ax.set_xlabel('Packet Count')
    ax.set_ylabel('Anomaly Score')
    ax.grid(True, alpha=0.3)

    # Summary panel
    ax = axes[1, 1]
    ax.axis('off')
    anomaly_count = int((predictions == -1).sum())
    total_count = len(scores)
    summary_text = (
        f"Total windows: {total_count}\n"
        f"Anomalies: {anomaly_count} ({(anomaly_count / total_count * 100):.1f}%)\n"
        f"Mean anomaly score: {np.mean(viz_scores):.4f}\n"
        f"Min anomaly score: {np.min(viz_scores):.4f}\n"
        f"Max anomaly score: {np.max(viz_scores):.4f}"
    )
    ax.text(0.05, 0.9, summary_text, transform=ax.transAxes, fontsize=10, va='top',
            bbox=dict(boxstyle='round', facecolor='#f0f0f0', alpha=0.8))

    plt.tight_layout()
    out_file = output_dir / f"{name_stem}_inference.png"
    plt.savefig(out_file, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"💾 Saved visualization: {out_file.name}")


def main():
    print("="*80)
    print("PRODUCTION INFERENCE PIPELINE")
    print("="*80)
    
    # Configuration
    pcapng_file = ROOT / 'data' / 'raw' / 'local_captures' / '14-02-2026.pcapng'
    pcap_file = ROOT / 'data' / 'raw' / 'local_captures' / '14-02-2026.pcap'
    features_json = ROOT / 'data' / 'processed' / 'local_captures' / '14-02-2026_features.json'
    
    # Validate input
    if not pcapng_file.exists():
        print(f"❌ Input file not found: {pcapng_file}")
        sys.exit(1)
    
    print(f"\n📁 Input file: {pcapng_file.name}")
    
    # Step 1: Convert
    try:
        pcap_file = convert_pcapng_to_pcap(pcapng_file, pcap_file)
    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        sys.exit(1)
    
    # Step 2: Extract
    try:
        features_json = extract_features(pcap_file, features_json)
    except Exception as e:
        print(f"❌ Feature extraction failed: {e}")
        sys.exit(1)
    
    # Step 3: Infer
    try:
        results, df, predictor = run_inference(features_json, model_type='combined')
    except Exception as e:
        print(f"❌ Inference failed: {e}")
        sys.exit(1)
    
    # Display results
    print("\n" + "="*80)
    print("INFERENCE RESULTS")
    print("="*80)
    
    print(f"\n📊 Summary:")
    print(f"  • Total windows: {results['n_windows']}")
    print(f"  • Normal: {results['n_windows'] - results['anomaly_count']} ({100*(1-results['anomaly_ratio']):.1f}%)")
    print(f"  • Anomalies: {results['anomaly_count']} ({100*results['anomaly_ratio']:.1f}%)")
    print(f"  • Mean score: {results['scores'].mean():.4f}")
    print(f"  • Min score: {results['scores'].min():.4f}")
    print(f"  • Max score: {results['scores'].max():.4f}")
    
    # Add predictions to dataframe
    df['score'] = results['scores']
    df['anomaly'] = results['predictions']
    df['is_anomaly'] = results['predictions'] == -1
    
    # Save results
    output_dir = ROOT / 'docs' / 'model_insight'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save predictions
    pred_file = output_dir / '14-02-2026_predictions.json'
    with open(pred_file, 'w') as f:
        json.dump({
            'model': results['model_used'],
            'total_windows': results['n_windows'],
            'anomaly_count': int(results['anomaly_count']),
            'anomaly_pct': float(results['anomaly_ratio'] * 100),
            'mean_score': float(results['scores'].mean()),
            'scores': results['scores'].tolist(),
            'predictions': results['predictions'].tolist(),
        }, f, indent=2)
    print(f"\n💾 Saved predictions: {pred_file.name}")

    # Generate insights
    generator = InsightGenerator(max_alerts=15)
    insights = generator.generate(df.to_dict('records'))
    insights_file = output_dir / '14-02-2026_insights.json'
    with open(insights_file, 'w') as f:
        json.dump(insights, f, indent=2)
    print(f"💾 Saved insights: {insights_file.name}")
    
    # Save detailed results
    detail_file = output_dir / '14-02-2026_detailed.json'
    with open(detail_file, 'w') as f:
        json.dump(df.to_dict('records'), f, indent=2)
    print(f"💾 Saved detailed results: {detail_file.name}")

    # Create visualization
    create_visualizations(df, results, output_dir, '14-02-2026')
    
    print("\n" + "="*80)
    print("✅ PRODUCTION INFERENCE COMPLETE")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()
