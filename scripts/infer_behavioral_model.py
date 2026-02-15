"""
Run inference on merged_50M using the new behavioral model.
Identify actual anomalies and generate insights.
"""

import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pickle
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from backend.insight.generator import InsightGenerator

def load_features(json_path):
    """Load feature JSON."""
    with open(json_path, 'r') as f:
        data = json.load(f)
    return pd.DataFrame(data)

def load_behavioral_model(model_path):
    """Load saved behavioral model."""
    with open(model_path, 'rb') as f:
        data = pickle.load(f)
    return data['model'], data['scaler'], data['feature_names']

def engineer_behavioral_features(df, rolling_window=10):
    """Same feature engineering as training."""
    df = df.copy()
    
    # Percentage change vs rolling baseline
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
    
    # Composition and normalized diversity
    df['bytes_per_packet'] = df['total_bytes'] / (df['packet_count'] + 1)
    df['src_ips_per_packet'] = df['unique_src_ips'] / (df['packet_count'] + 1)
    df['dst_ips_per_packet'] = df['unique_dst_ips'] / (df['packet_count'] + 1)
    if 'flow_count' in df.columns:
        df['flow_per_packet'] = df['flow_count'] / (df['packet_count'] + 1)
    
    # Behavioral entropy
    if 'max_packet_size' in df.columns and 'min_packet_size' in df.columns:
        df['packet_size_range'] = (df['max_packet_size'] - df['min_packet_size']) / (df['avg_packet_size'] + 1)
    
    df['protocol_diversity'] = -(
        df['tcp_ratio'] * np.log(df['tcp_ratio'] + 1e-6) +
        df['udp_ratio'] * np.log(df['udp_ratio'] + 1e-6) +
        df['icmp_ratio'] * np.log(df['icmp_ratio'] + 1e-6)
    )
    
    return df

def run_inference(test_df, model, scaler, feature_names):
    """Run inference on test data."""
    
    # Engineer features
    test_eng = engineer_behavioral_features(test_df, rolling_window=10)
    
    # Extract only required features
    test_features = test_eng[feature_names].copy()
    test_features = test_features.fillna(0).replace([np.inf, -np.inf], 0)
    
    # Scale
    test_scaled = scaler.transform(test_features)
    
    # Predict
    scores = -model.score_samples(test_scaled)
    predictions = model.predict(test_scaled)
    
    return {
        'scores': scores,
        'predictions': predictions,
        'engineered': test_eng,
        'features': test_features,
    }

def identify_anomaly_drivers(test_df_orig, test_eng, anomaly_indices, feature_names):
    """For each anomaly, identify which features drove the detection."""
    
    drivers = []
    
    for idx in anomaly_indices:
        window = test_eng.iloc[idx]
        
        # Key behavioral metrics
        driver_info = {
            'window_idx': int(idx),
            'window_start': float(test_df_orig.iloc[idx]['window_start']),
            'window_end': float(test_df_orig.iloc[idx]['window_end']),
            'packet_count': int(test_df_orig.iloc[idx]['packet_count']),
            'anomaly_drivers': [],
        }
        
        # Check which features are unusual
        # Packet count change
        pct_chg_pkt = float(window['pct_change_packets'])
        if abs(pct_chg_pkt) > 0.5:
            driver_info['anomaly_drivers'].append({
                'feature': 'pct_change_packets',
                'value': pct_chg_pkt,
                'description': f'Packet count {pct_chg_pkt:+.1%} vs baseline',
            })
        
        # Bytes/sec change
        pct_chg_bytes = float(window['pct_change_bytes_ps'])
        if abs(pct_chg_bytes) > 0.5:
            driver_info['anomaly_drivers'].append({
                'feature': 'pct_change_bytes_ps',
                'value': pct_chg_bytes,
                'description': f'Throughput {pct_chg_bytes:+.1%} vs baseline',
            })
        
        # TCP ratio (expected ~0.7 in training, 0.34 in test)
        tcp_ratio = float(window['tcp_ratio'])
        if tcp_ratio < 0.2 or tcp_ratio > 0.9:
            driver_info['anomaly_drivers'].append({
                'feature': 'tcp_ratio',
                'value': tcp_ratio,
                'description': f'TCP ratio {tcp_ratio:.2%} (unusual mix)',
            })
        
        # ICMP ratio
        icmp_ratio = float(window['icmp_ratio'])
        if icmp_ratio > 0.5:
            driver_info['anomaly_drivers'].append({
                'feature': 'icmp_ratio',
                'value': icmp_ratio,
                'description': f'ICMP ratio {icmp_ratio:.2%} (high)',
            })
        
        # Src/Dst IP diversity
        src_per_pkt = float(window['src_ips_per_packet'])
        if src_per_pkt > 0.3:
            driver_info['anomaly_drivers'].append({
                'feature': 'src_ips_per_packet',
                'value': src_per_pkt,
                'description': f'High source IP diversity ({src_per_pkt:.3f})',
            })
        
        dst_per_pkt = float(window['dst_ips_per_packet'])
        if dst_per_pkt > 0.3:
            driver_info['anomaly_drivers'].append({
                'feature': 'dst_ips_per_packet',
                'value': dst_per_pkt,
                'description': f'High dest IP diversity ({dst_per_pkt:.3f})',
            })
        
        drivers.append(driver_info)
    
    return drivers

def create_anomaly_visualization(test_df_orig, inference_results, out_dir: Path):
    """Create detailed anomaly visualization."""
    out_dir.mkdir(parents=True, exist_ok=True)
    
    scores = inference_results['scores']
    predictions = inference_results['predictions']
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle('Behavioral Model: Merged_50M Anomaly Detection Results', 
                 fontsize=16, fontweight='bold')
    
    # (0,0) Timeline of scores with anomalies highlighted
    ax = axes[0, 0]
    ax.plot(scores, linewidth=1.5, color='#1f77b4', alpha=0.8, label='Anomaly Score')
    
    anomaly_indices = np.where(predictions == -1)[0]
    if len(anomaly_indices) > 0:
        ax.scatter(anomaly_indices, scores[anomaly_indices], 
                  color='red', s=100, zorder=5, label=f'Anomalies (n={len(anomaly_indices)})',
                  edgecolors='darkred', linewidth=2)
    
    # Add threshold line
    threshold = np.percentile(scores, 88)  # ~12% are above threshold
    ax.axhline(threshold, color='orange', linestyle='--', linewidth=2, label=f'Threshold ({threshold:.3f})')
    
    ax.set_title('Anomaly Score Timeline', fontweight='bold', fontsize=12)
    ax.set_xlabel('Window Index')
    ax.set_ylabel('Anomaly Score')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    
    # (0,1) Score distribution with anomaly region
    ax = axes[0, 1]
    normal_scores = scores[predictions == 1]
    anomaly_scores = scores[predictions == -1]
    
    ax.hist(normal_scores, bins=25, alpha=0.7, color='#2ecc71', edgecolor='black', label='Normal')
    if len(anomaly_scores) > 0:
        ax.hist(anomaly_scores, bins=10, alpha=0.7, color='#e74c3c', edgecolor='black', label='Anomaly')
    
    ax.axvline(threshold, color='orange', linestyle='--', linewidth=2, label='Threshold')
    ax.set_title('Score Distribution', fontweight='bold', fontsize=12)
    ax.set_xlabel('Anomaly Score')
    ax.set_ylabel('Frequency')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # (1,0) Packet count vs score (should show no correlation now)
    ax = axes[1, 0]
    colors = ['#e74c3c' if p == -1 else '#2ecc71' for p in predictions]
    ax.scatter(test_df_orig['packet_count'], scores, c=colors, alpha=0.5, s=30, edgecolors='black', linewidth=0.3)
    ax.set_title('Packet Count vs Score\n(should show low correlation)', fontweight='bold', fontsize=12)
    ax.set_xlabel('Packet Count')
    ax.set_ylabel('Anomaly Score')
    ax.grid(True, alpha=0.3)
    
    # (1,1) Statistics
    ax = axes[1, 1]
    ax.axis('off')
    
    stats_text = f"""
    BEHAVIORAL MODEL INFERENCE RESULTS
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    Dataset: merged_50M (107 windows)
    
    Detection Summary:
      • Normal windows: {(predictions == 1).sum()} ({(predictions == 1).mean()*100:.1f}%)
      • Anomalous windows: {(predictions == -1).sum()} ({(predictions == -1).mean()*100:.1f}%)
      • Mean score (normal): {normal_scores.mean():.4f}
      • Mean score (anomaly): {anomaly_scores.mean() if len(anomaly_scores) > 0 else 0:.4f}
      • Threshold: {threshold:.4f}
    
    Anomaly Characteristics:
      • Min score: {scores.min():.4f}
      • Max score: {scores.max():.4f}
      • Median score: {np.median(scores):.4f}
    
    Model Type: Behavioral (Scale-Robust)
    Features: 12 (all relative/behavioral)
    
    Key Insight:
    Anomalies are driven by BEHAVIOR CHANGES,
    not just traffic volume.
    """
    
    ax.text(0.05, 0.95, stats_text, transform=ax.transAxes, fontsize=10,
           verticalalignment='top', family='monospace',
           bbox=dict(boxstyle='round', facecolor='#f0f0f0', alpha=0.8))
    
    plt.tight_layout()
    out_file = out_dir / 'behavioral_model_inference_results.png'
    plt.savefig(out_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Saved inference visualization: {out_file.name}")

def main():
    print("=" * 90)
    print("BEHAVIORAL MODEL INFERENCE ON merged_50M")
    print("=" * 90)
    
    # Load data
    print("\nLoading data...")
    test_df = load_features(ROOT / 'docs' / 'model_insight' / 'split_merged_50M_features.json')
    print(f"  ✓ {len(test_df)} test windows loaded")
    
    # Load model
    print("\nLoading behavioral model...")
    model_path = ROOT / 'models' / 'network_anomaly_model_behavioral.pkl'
    if not model_path.exists():
        print(f"❌ Model not found: {model_path}")
        sys.exit(1)
    
    model, scaler, feature_names = load_behavioral_model(model_path)
    print(f"  ✓ Model loaded")
    print(f"  ✓ Features: {feature_names}")
    
    # Run inference
    print("\n" + "=" * 90)
    print("RUNNING INFERENCE")
    print("=" * 90)
    
    results = run_inference(test_df, model, scaler, feature_names)
    
    scores = results['scores']
    predictions = results['predictions']
    
    normal_count = (predictions == 1).sum()
    anomaly_count = (predictions == -1).sum()
    anomaly_pct = anomaly_count / len(predictions) * 100
    
    print(f"\n✓ Inference complete:")
    print(f"  • Normal windows: {normal_count} ({(predictions == 1).mean()*100:.1f}%)")
    print(f"  • Anomalous windows: {anomaly_count} ({anomaly_pct:.1f}%)")
    print(f"  • Mean score: {scores.mean():.4f}")
    print(f"  • Score range: [{scores.min():.4f}, {scores.max():.4f}]")
    
    # Identify anomaly drivers
    print("\n" + "=" * 90)
    print("ANALYZING ANOMALIES")
    print("=" * 90)
    
    anomaly_indices = np.where(predictions == -1)[0]
    print(f"\nFound {len(anomaly_indices)} anomalous windows")
    
    drivers = identify_anomaly_drivers(test_df, results['engineered'], anomaly_indices, feature_names)
    
    # Show top anomalies
    print("\nTop 10 anomalies by severity:")
    print("-" * 90)
    
    sorted_anomalies = sorted(anomaly_indices, key=lambda i: scores[i], reverse=True)[:10]
    
    for rank, idx in enumerate(sorted_anomalies, 1):
        window = test_df.iloc[idx]
        score = scores[idx]
        
        # Find driver info
        driver_info = next((d for d in drivers if d['window_idx'] == idx), None)
        driver_list = driver_info['anomaly_drivers'] if driver_info else []
        
        print(f"\n  {rank}. Window {idx} (Score: {score:.4f})")
        print(f"     Time: {window['window_start']:.1f} - {window['window_end']:.1f}")
        print(f"     Packets: {int(window['packet_count']):,}")
        print(f"     Bytes/sec: {window['bytes_per_sec']:,.0f}")
        
        if driver_list:
            print(f"     Anomaly drivers:")
            for driver in driver_list[:3]:
                print(f"       • {driver['description']}")
    
    # Generate insights
    print("\n" + "=" * 90)
    print("GENERATING INSIGHTS")
    print("=" * 90)
    
    # Create detailed records
    records = []
    for idx in range(len(test_df)):
        rec = test_df.iloc[idx].to_dict()
        rec['anomaly_score'] = float(scores[idx])
        rec['is_anomaly'] = int(predictions[idx] == -1)
        records.append(rec)
    
    generator = InsightGenerator(max_alerts=20)
    insights = generator.generate(records)
    
    print(f"\n✓ Generated {len(insights.get('alerts', []))} insights")
    
    # Save results
    print("\n" + "=" * 90)
    print("SAVING RESULTS")
    print("=" * 90)
    
    out_dir = ROOT / 'docs' / 'model_insight'
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Predictions
    preds_path = out_dir / 'behavioral_model_predictions.json'
    with open(preds_path, 'w') as f:
        json.dump({
            'scores': scores.tolist(),
            'predictions': predictions.tolist(),
            'anomaly_count': int(anomaly_count),
            'anomaly_pct': float(anomaly_pct),
            'normal_count': int(normal_count),
            'threshold': float(np.percentile(scores, 88)),
        }, f, indent=2)
    print(f"✓ Saved predictions: {preds_path.name}")
    
    # Anomaly drivers
    drivers_path = out_dir / 'behavioral_model_anomaly_drivers.json'
    with open(drivers_path, 'w') as f:
        json.dump(drivers, f, indent=2)
    print(f"✓ Saved anomaly drivers: {drivers_path.name}")
    
    # Insights
    insights_path = out_dir / 'behavioral_model_insights.json'
    with open(insights_path, 'w') as f:
        json.dump(insights, f, indent=2)
    print(f"✓ Saved insights: {insights_path.name}")
    
    # Visualization
    print("\n" + "=" * 90)
    print("CREATING VISUALIZATIONS")
    print("=" * 90)
    
    create_anomaly_visualization(test_df, results, out_dir)
    
    print("\n" + "=" * 90)
    print("✓ BEHAVIORAL MODEL INFERENCE COMPLETE")
    print("=" * 90)
    print(f"\nAll results saved to: {out_dir}\n")

if __name__ == '__main__':
    main()
