"""
Extract features from pre-split chunks, merge JSONs, run inference, generate insights
and create academic + professional visualizations.

Usage:
    python scripts/extract_merge_analyze.py --chunks-dir data/raw/split_merged_50M

This assumes chunks already exist and just needs extraction → merge → analyze → viz.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
import time
import numpy as np

# Use non-interactive backend
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

# Add repo root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from backend.ml.production_inference import predict_with_feature_engineering
from backend.insight.generator import InsightGenerator


def run_rust_extractor(pcap_path: Path, output_json: Path):
    """Run Rust extractor on a single PCAP chunk."""
    extractor_path = ROOT / 'backend' / 'features' / 'rust_extractor' / 'target' / 'release' / 'rust_extractor.exe'
    if not extractor_path.exists():
        raise FileNotFoundError(f"Rust extractor not found at {extractor_path}")

    output_json.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(extractor_path), str(pcap_path), str(output_json)]
    
    print(f"  Extracting: {pcap_path.name} → {output_json.name}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    
    if res.returncode != 0:
        print(f"    ERROR: {res.stderr}")
        raise RuntimeError(f"Extractor failed on {pcap_path}")
    
    # Parse stdout for window count
    for line in res.stdout.split('\n'):
        if 'windows' in line.lower():
            print(f"    {line.strip()}")
    
    return output_json


def merge_feature_jsons(json_paths, merged_path: Path):
    """Merge all feature JSONs into one."""
    merged = []
    total_windows = 0
    
    for p in sorted(json_paths):
        print(f"  Merging: {p.name}")
        with open(p, 'r') as f:
            data = json.load(f)
        if isinstance(data, list):
            merged.extend(data)
            total_windows += len(data)
        else:
            merged.append(data)
            total_windows += 1
    
    merged_path.parent.mkdir(parents=True, exist_ok=True)
    with open(merged_path, 'w') as f:
        json.dump(merged, f)
    
    print(f"✓ Merged {len(json_paths)} files → {total_windows} total windows")
    return merged_path, total_windows


def generate_visualization_academic(df, results, insights, out_dir: Path, name_stem: str):
    """Academic 2x2 grid with histograms, boxplots, scatter, timeline."""
    out_dir.mkdir(parents=True, exist_ok=True)
    sns.set_style('whitegrid')
    
    scores = results['scores']
    preds = results['predictions']
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f'Anomaly Detection Analysis - {name_stem}', fontsize=16, fontweight='bold')
    
    # (0,0) Score distribution
    sns.histplot(scores, kde=True, ax=axes[0, 0], color='navy', bins=40)
    axes[0, 0].axvline(scores.mean(), color='red', linestyle='--', linewidth=2, label=f'μ={scores.mean():.3f}')
    axes[0, 0].set_title('Anomaly Score Distribution', fontweight='bold')
    axes[0, 0].set_xlabel('Score')
    axes[0, 0].legend()
    
    # (0,1) Box plot: Normal vs Anomaly
    normal_scores = scores[preds == 1]
    anomaly_scores = scores[preds == -1]
    bp = axes[0, 1].boxplot([normal_scores, anomaly_scores],
                             labels=[f'Normal (n={len(normal_scores)})', 
                                    f'Anomaly (n={len(anomaly_scores)})'],
                             patch_artist=True)
    bp['boxes'][0].set_facecolor('#2ecc71')
    if len(anomaly_scores) > 0:
        bp['boxes'][1].set_facecolor('#e74c3c')
    axes[0, 1].set_title('Prediction Classes', fontweight='bold')
    axes[0, 1].set_ylabel('Score')
    axes[0, 1].grid(True, alpha=0.3)
    
    # (1,0) Packet count vs Score scatter
    axes[1, 0].scatter(df['packet_count'], scores, c=preds, cmap='RdYlGn_r', alpha=0.5, s=20)
    axes[1, 0].set_xlabel('Packet Count')
    axes[1, 0].set_ylabel('Anomaly Score')
    axes[1, 0].set_title('Packet Count vs Score', fontweight='bold')
    axes[1, 0].grid(True, alpha=0.3)
    
    # (1,1) Timeline
    axes[1, 1].plot(scores, marker='.', linewidth=0.8, markersize=3, color='navy')
    axes[1, 1].fill_between(range(len(scores)), scores, alpha=0.2, color='navy')
    axes[1, 1].set_title('Anomaly Score Timeline', fontweight='bold')
    axes[1, 1].set_xlabel('Window Index')
    axes[1, 1].set_ylabel('Score')
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    out_file = out_dir / f"{name_stem}_academic.png"
    plt.savefig(out_file, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"✓ Saved academic visualization: {out_file.name}")
    return out_file


def generate_visualization_professional(df, results, insights, out_dir: Path, name_stem: str):
    """Professional wide dashboard with 4 main panels."""
    out_dir.mkdir(parents=True, exist_ok=True)
    plt.style.use('seaborn-v0_8-darkgrid')
    
    scores = results['scores']
    preds = results['predictions']
    
    fig = plt.figure(figsize=(18, 10))
    gs = fig.add_gridspec(3, 4, hspace=0.3, wspace=0.3)
    
    # Title
    fig.suptitle(f'Network Anomaly Detection Report: {name_stem}', 
                 fontsize=18, fontweight='bold', y=0.98)
    
    # Panel 1: Score histogram (top-left, spans 2 rows)
    ax1 = fig.add_subplot(gs[:2, 0])
    ax1.hist(scores, bins=50, color='#2E86AB', edgecolor='black', alpha=0.7)
    ax1.axvline(scores.mean(), color='red', linestyle='--', linewidth=2, label=f'Mean: {scores.mean():.3f}')
    ax1.set_title('Score Distribution', fontweight='bold', fontsize=11)
    ax1.set_xlabel('Anomaly Score')
    ax1.set_ylabel('Frequency')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Panel 2: Box plot comparison (top-middle-left)
    ax2 = fig.add_subplot(gs[0, 1])
    normal_scores = scores[preds == 1]
    anomaly_scores = scores[preds == -1]
    bp = ax2.boxplot([normal_scores, anomaly_scores],
                      labels=['Normal', 'Anomaly'],
                      patch_artist=True, widths=0.6)
    bp['boxes'][0].set_facecolor('#2ecc71')
    if len(anomaly_scores) > 0:
        bp['boxes'][1].set_facecolor('#e74c3c')
    ax2.set_title('Classification', fontweight='bold', fontsize=11)
    ax2.set_ylabel('Score')
    ax2.grid(True, alpha=0.3, axis='y')
    
    # Panel 3: Statistics table (top-middle-right)
    ax3 = fig.add_subplot(gs[0, 2:])
    ax3.axis('off')
    stats_text = f"""
    ━━━━━ STATISTICS ━━━━━
    Total Windows:     {len(scores):,}
    Normal:            {len(normal_scores):,}
    Anomalies:         {len(anomaly_scores):,}
    Anomaly Rate:      {(len(anomaly_scores)/len(scores)*100):.2f}%
    
    ━━━━━ SCORE STATS ━━━━━
    Mean:              {scores.mean():.4f}
    Std Dev:           {scores.std():.4f}
    Min:               {scores.min():.4f}
    Max:               {scores.max():.4f}
    Median:            {np.median(scores):.4f}
    
    ━━━━━ ALERTS ━━━━━
    Generated:         {len(insights.get('alerts', []))}
    """
    ax3.text(0.05, 0.95, stats_text, transform=ax3.transAxes, fontsize=10,
            verticalalignment='top', family='monospace',
            bbox=dict(boxstyle='round', facecolor='#f0f0f0', alpha=0.8))
    
    # Panel 4: Packet count vs Score (middle-left)
    ax4 = fig.add_subplot(gs[1, 1:3])
    cmap_dict = {1: '#2ecc71', -1: '#e74c3c'}
    colors = [cmap_dict[int(p)] for p in preds]
    ax4.scatter(df['packet_count'], scores, c=colors, alpha=0.5, s=30, edgecolors='black', linewidth=0.3)
    ax4.set_xlabel('Packet Count', fontweight='bold')
    ax4.set_ylabel('Anomaly Score', fontweight='bold')
    ax4.set_title('Packet Count vs Score', fontweight='bold', fontsize=11)
    ax4.grid(True, alpha=0.3)
    
    # Panel 5: Bytes/sec vs Anomaly (middle-right)
    ax5 = fig.add_subplot(gs[1, 3])
    try:
        ax5.scatter(df['bytes_per_sec'], scores, c=colors, alpha=0.5, s=30, edgecolors='black', linewidth=0.3)
        ax5.set_xlabel('Bytes/sec', fontweight='bold', fontsize=9)
        ax5.set_ylabel('Score', fontweight='bold', fontsize=9)
        ax5.set_title('Throughput vs Score', fontweight='bold', fontsize=11)
        ax5.grid(True, alpha=0.3)
    except Exception:
        ax5.text(0.5, 0.5, 'N/A', ha='center', va='center', transform=ax5.transAxes)
    
    # Panel 6: Timeline (bottom, spans all columns)
    ax6 = fig.add_subplot(gs[2, :])
    ax6.plot(scores, linewidth=1.2, color='#1f77b4', alpha=0.8)
    ax6.fill_between(range(len(scores)), scores, alpha=0.2, color='#1f77b4')
    
    # Highlight anomalies on timeline
    anomaly_indices = np.where(preds == -1)[0]
    if len(anomaly_indices) > 0:
        ax6.scatter(anomaly_indices, scores[anomaly_indices], color='red', s=50, 
                   zorder=5, label=f'Anomalies (n={len(anomaly_indices)})', edgecolors='darkred', linewidth=1)
        ax6.legend(loc='upper right')
    
    ax6.set_title('Anomaly Score Timeline', fontweight='bold', fontsize=11)
    ax6.set_xlabel('Window Index', fontweight='bold')
    ax6.set_ylabel('Score', fontweight='bold')
    ax6.grid(True, alpha=0.3)
    
    plt.tight_layout()
    out_file = out_dir / f"{name_stem}_professional.png"
    plt.savefig(out_file, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"✓ Saved professional visualization: {out_file.name}")
    return out_file


def main():
    parser = argparse.ArgumentParser(description='Extract, merge, analyze, and visualize pre-split PCAP chunks')
    parser.add_argument('--chunks-dir', required=True, help='Directory containing split PCAP chunks')
    args = parser.parse_args()
    
    chunks_dir = Path(args.chunks_dir)
    if not chunks_dir.exists():
        print(f"❌ Chunks directory not found: {chunks_dir}")
        sys.exit(1)
    
    # Find all .pcap files in chunks_dir
    pcap_files = sorted(chunks_dir.glob('*.pcap'))
    if not pcap_files:
        print(f"❌ No .pcap files found in {chunks_dir}")
        sys.exit(1)
    
    print(f"Found {len(pcap_files)} chunk(s) to process\n")
    
    # Output directories
    out_dir = ROOT / 'docs' / 'model_insight'
    temp_features_dir = ROOT / 'data' / 'processed' / f'features_{chunks_dir.stem}'
    merged_features = out_dir / f"{chunks_dir.stem}_features.json"
    
    # 1) Extract features from each chunk
    print("=" * 80)
    print("STEP 1: EXTRACTING FEATURES FROM CHUNKS")
    print("=" * 80)
    
    feature_files = []
    for idx, pcap in enumerate(pcap_files, 1):
        out_json = temp_features_dir / f"{pcap.stem}_features.json"
        try:
            run_rust_extractor(pcap, out_json)
            feature_files.append(out_json)
            print(f"  [{idx}/{len(pcap_files)}] ✓ Done\n")
        except Exception as e:
            print(f"  ❌ Failed: {e}\n")
            sys.exit(1)
    
    # 2) Merge features
    print("=" * 80)
    print("STEP 2: MERGING FEATURE JSONs")
    print("=" * 80)
    
    merged_features, total_windows = merge_feature_jsons(feature_files, merged_features)
    
    # 3) Run inference & generate insights
    print("\n" + "=" * 80)
    print("STEP 3: RUNNING INFERENCE & GENERATING INSIGHTS")
    print("=" * 80)
    
    print(f"\nProcessing {total_windows:,} windows...")
    results = predict_with_feature_engineering(str(merged_features))
    
    print(f"✓ Inference complete:")
    print(f"  • Anomalies detected: {results['anomaly_count']} ({results['anomaly_percentage']:.2f}%)")
    print(f"  • Avg score: {results['scores'].mean():.4f}")
    
    generator = InsightGenerator(max_alerts=15)
    records = results['detailed_results'].to_dict('records')
    insights = generator.generate(records)
    
    print(f"✓ Generated {len(insights.get('alerts', []))} alerts")
    
    # Save insights & predictions
    insights_file = out_dir / f"{chunks_dir.stem}_insights.json"
    preds_file = out_dir / f"{chunks_dir.stem}_predictions.json"
    
    with open(insights_file, 'w') as f:
        json.dump(insights, f, indent=2)
    with open(preds_file, 'w') as f:
        json.dump(results['detailed_results'].to_dict('records'), f, indent=2)
    
    print(f"✓ Saved insights: {insights_file.name}")
    print(f"✓ Saved predictions: {preds_file.name}")
    
    # 4) Create visualizations
    print("\n" + "=" * 80)
    print("STEP 4: GENERATING VISUALIZATIONS")
    print("=" * 80)
    
    df = results['detailed_results']
    generate_visualization_academic(df, results, insights, out_dir, chunks_dir.stem)
    generate_visualization_professional(df, results, insights, out_dir, chunks_dir.stem)
    
    # 5) Generate report
    print("\n" + "=" * 80)
    print("STEP 5: GENERATING REPORT")
    print("=" * 80)
    
    report_path = out_dir / f"ANALYSIS_REPORT_{chunks_dir.stem}.md"
    with open(report_path, 'w') as f:
        f.write(f"# Analysis Report - {chunks_dir.stem}\n\n")
        f.write(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## Summary\n")
        f.write(f"- Total Windows Analyzed: {total_windows:,}\n")
        f.write(f"- Anomalies Detected: {results['anomaly_count']} ({results['anomaly_percentage']:.2f}%)\n")
        f.write(f"- Mean Anomaly Score: {results['scores'].mean():.4f}\n")
        f.write(f"- Alerts Generated: {len(insights.get('alerts', []))}\n\n")
        f.write(f"## Insights\n")
        f.write(json.dumps(insights, indent=2))
    
    print(f"✓ Saved report: {report_path.name}")
    
    print("\n" + "=" * 80)
    print("✓ ALL DONE!")
    print("=" * 80)
    print(f"\nOutputs saved to: {out_dir}\n")

if __name__ == '__main__':
    main()
