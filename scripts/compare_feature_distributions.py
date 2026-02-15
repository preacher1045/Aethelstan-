"""
Compare feature distributions between training data and merged_50M test data
to identify dataset/distribution mismatches.
"""

import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

def load_features(json_path):
    """Load feature JSON and convert to DataFrame."""
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    print(f"Loaded {len(df)} windows from {Path(json_path).name}")
    print(f"Columns: {list(df.columns)[:10]}...\n")
    return df

def get_summary_stats(df, name):
    """Get statistical summary of key features."""
    key_features = ['packet_count', 'total_bytes', 'avg_packet_size', 
                    'packets_per_sec', 'bytes_per_sec', 'unique_src_ips', 
                    'unique_dst_ips', 'flow_count', 'tcp_ratio', 'udp_ratio', 'icmp_ratio']
    
    stats = {}
    for feat in key_features:
        if feat in df.columns:
            stats[feat] = {
                'mean': df[feat].mean(),
                'std': df[feat].std(),
                'median': df[feat].median(),
                'min': df[feat].min(),
                'max': df[feat].max(),
                'q25': df[feat].quantile(0.25),
                'q75': df[feat].quantile(0.75),
            }
    
    return stats

def compare_distributions(train_stats, test_stats):
    """Compare statistics and identify divergences."""
    print("=" * 90)
    print("FEATURE DISTRIBUTION COMPARISON")
    print("=" * 90)
    print(f"{'Feature':<20} {'Train Mean':<15} {'Test Mean':<15} {'Divergence %':<15} {'Status':<15}")
    print("-" * 90)
    
    divergences = []
    for feat in train_stats.keys():
        train_mean = train_stats[feat]['mean']
        test_mean = test_stats[feat]['mean']
        
        if train_mean == 0:
            pct_diff = 0
        else:
            pct_diff = abs((test_mean - train_mean) / train_mean) * 100
        
        status = "⚠️  MISMATCH" if pct_diff > 30 else "✓ Similar"
        print(f"{feat:<20} {train_mean:<15.2f} {test_mean:<15.2f} {pct_diff:<15.1f}% {status:<15}")
        
        if pct_diff > 30:
            divergences.append((feat, pct_diff, train_mean, test_mean))
    
    print("-" * 90)
    return divergences

def create_comparison_visualization(train_df, test_df, out_dir: Path):
    """Create side-by-side distribution plots."""
    key_features = ['packet_count', 'total_bytes', 'bytes_per_sec', 
                    'unique_src_ips', 'unique_dst_ips', 'icmp_ratio']
    
    fig, axes = plt.subplots(3, 2, figsize=(14, 12))
    fig.suptitle('Feature Distribution Comparison: Training vs Test Data', 
                 fontsize=16, fontweight='bold')
    
    axes = axes.flatten()
    
    for idx, feat in enumerate(key_features):
        if feat in train_df.columns and feat in test_df.columns:
            ax = axes[idx]
            
            # Plot histograms
            ax.hist(train_df[feat], bins=30, alpha=0.6, label='Training (n=1988)', 
                   color='blue', edgecolor='black')
            ax.hist(test_df[feat], bins=15, alpha=0.6, label='Test (n=107)', 
                   color='red', edgecolor='black')
            
            ax.set_title(f'{feat}', fontweight='bold')
            ax.set_xlabel('Value')
            ax.set_ylabel('Frequency')
            ax.legend()
            ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    out_file = out_dir / 'feature_distribution_comparison.png'
    plt.savefig(out_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\n✓ Saved comparison visualization: {out_file.name}")

def main():
    # Find feature files
    model_insight_dir = ROOT / 'docs' / 'model_insight'
    
    # Use training data used for production model
    training_json = ROOT / 'data' / 'processed' / 'test_net_traffic_features.json'
    test_json = model_insight_dir / 'split_merged_50M_features.json'
    
    print("=" * 90)
    print("LOADING DATA")
    print("=" * 90)
    
    # Load data - handle both JSON and JSONL formats
    print("Loading training data...")
    if str(training_json).endswith('.jsonl'):
        train_data = []
        with open(training_json, 'r') as f:
            for line in f:
                if line.strip():
                    train_data.append(json.loads(line))
        train_df = pd.DataFrame(train_data)
    else:
        train_df = load_features(training_json)
    
    print(f"Loaded {len(train_df)} training windows\n")
    
    print("Loading test data...")
    test_df = load_features(test_json)
    
    # Compute statistics
    print("=" * 90)
    print("COMPUTING STATISTICS")
    print("=" * 90)
    
    train_stats = get_summary_stats(train_df, "Training")
    test_stats = get_summary_stats(test_df, "Test")
    
    # Compare
    print()
    divergences = compare_distributions(train_stats, test_stats)
    
    # Summary
    print("\n" + "=" * 90)
    print("SUMMARY")
    print("=" * 90)
    
    if len(divergences) > 3:
        print(f"\n⚠️  HIGH MISMATCH DETECTED!")
        print(f"   {len(divergences)} features show >30% divergence:")
        for feat, pct, train_mean, test_mean in divergences:
            ratio = test_mean / train_mean if train_mean != 0 else 0
            print(f"   • {feat}: Test is {ratio:.2f}x Training ({pct:.1f}% diff)")
        print("\n   This explains the 100% anomaly detection rate!")
        print("   The test data has significantly different characteristics than training data.")
    else:
        print(f"\n✓ Distributions relatively similar ({len(divergences)} minor divergences)")
    
    # Create visualization
    print("\n" + "=" * 90)
    print("CREATING VISUALIZATION")
    print("=" * 90)
    create_comparison_visualization(train_df, test_df, model_insight_dir)
    
    # Save detailed report
    report_path = model_insight_dir / 'DISTRIBUTION_COMPARISON_REPORT.md'
    with open(report_path, 'w') as f:
        f.write("# Feature Distribution Comparison Report\n\n")
        f.write(f"## Datasets\n")
        f.write(f"- **Training Data:** {len(train_df)} windows\n")
        f.write(f"- **Test Data (merged_50M):** {len(test_df)} windows\n\n")
        f.write(f"## Key Findings\n")
        f.write(f"- **Divergent Features:** {len(divergences)}\n")
        f.write(f"- **Status:** {'HIGH MISMATCH - Different traffic patterns detected' if len(divergences) > 3 else 'Acceptable variance'}\n\n")
        
        f.write(f"## Feature Divergences (>30%)\n")
        for feat, pct, train_mean, test_mean in divergences:
            f.write(f"- **{feat}**: {pct:.1f}% difference\n")
            f.write(f"  - Training mean: {train_mean:.2f}\n")
            f.write(f"  - Test mean: {test_mean:.2f}\n")
            f.write(f"  - Ratio: {test_mean/train_mean if train_mean != 0 else 0:.2f}x\n\n")
        
        f.write(f"## Interpretation\n")
        if len(divergences) > 3:
            f.write(f"The high number of divergences indicates that the test dataset has fundamentally different\n")
            f.write(f"network traffic characteristics than the training data. This causes the anomaly detection model\n")
            f.write(f"to flag all windows as anomalous because:\n\n")
            f.write(f"1. The feature values fall outside the learned normal distribution\n")
            f.write(f"2. The decision threshold was calibrated on different traffic patterns\n")
            f.write(f"3. High ICMP ratios and large flow counts are flagged as unusual\n\n")
            f.write(f"## Recommendations\n")
            f.write(f"1. **Retrain the model** on data matching merged_50M.pcap traffic patterns\n")
            f.write(f"2. **Adjust decision threshold** post-inference to reduce false positives\n")
            f.write(f"3. **Separate models** for different traffic types (normal vs enterprise vs ISP)\n")
            f.write(f"4. **Feature normalization** across different data sources\n")
        else:
            f.write(f"Distributions are acceptably similar. Other factors may explain high anomaly rate.\n")
    
    print(f"✓ Saved detailed report: {report_path.name}\n")
    
    print("=" * 90)
    print("✓ ANALYSIS COMPLETE")
    print("=" * 90)

if __name__ == '__main__':
    main()
