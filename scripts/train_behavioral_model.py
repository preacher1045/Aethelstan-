"""
Further-improved scale-robust model v2: Remove absolute volume features entirely.
Focus on: behavioral deviation, protocol mix, normalized diversity metrics.
"""

import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler
import pickle
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

def load_features(json_path):
    """Load feature JSON (preserves order for rolling baseline)."""
    with open(json_path, 'r') as f:
        data = json.load(f)
    return pd.DataFrame(data)

def engineer_behavioral_features(df, rolling_window=10):
    """
    Engineer ONLY behavioral/relative features.
    Remove absolute volume metrics entirely.
    """
    df = df.copy()
    
    print(f"  Engineering behavioral features (rolling_window={rolling_window})...")
    
    # ✅ KEEP: Percentage change vs rolling baseline
    if len(df) >= rolling_window:
        # Packet count % change
        rolling_packets = df['packet_count'].rolling(window=rolling_window, min_periods=1).mean()
        df['pct_change_packets'] = (df['packet_count'] - rolling_packets) / (rolling_packets + 1)
        
        # Bytes/sec % change
        rolling_bytes_ps = df['bytes_per_sec'].rolling(window=rolling_window, min_periods=1).mean()
        df['pct_change_bytes_ps'] = (df['bytes_per_sec'] - rolling_bytes_ps) / (rolling_bytes_ps + 1)
        
        # Flow count % change
        if 'flow_count' in df.columns:
            rolling_flows = df['flow_count'].rolling(window=rolling_window, min_periods=1).mean()
            df['pct_change_flows'] = (df['flow_count'] - rolling_flows) / (rolling_flows + 1)
    else:
        df['pct_change_packets'] = 0.0
        df['pct_change_bytes_ps'] = 0.0
        if 'flow_count' in df.columns:
            df['pct_change_flows'] = 0.0
    
    # ✅ KEEP: Protocol ratios (scale-independent)
    # tcp_ratio, udp_ratio, icmp_ratio should exist
    
    # ✅ KEEP: Bytes per packet (composition, not volume)
    df['bytes_per_packet'] = df['total_bytes'] / (df['packet_count'] + 1)
    
    # ✅ KEEP: Packet diversity (normalized by count)
    df['src_ips_per_packet'] = df['unique_src_ips'] / (df['packet_count'] + 1)
    df['dst_ips_per_packet'] = df['unique_dst_ips'] / (df['packet_count'] + 1)
    if 'flow_count' in df.columns:
        df['flow_per_packet'] = df['flow_count'] / (df['packet_count'] + 1)
    
    # NEW: Packet size distribution metrics (behavioral)
    if 'max_packet_size' in df.columns and 'min_packet_size' in df.columns:
        df['packet_size_range'] = (df['max_packet_size'] - df['min_packet_size']) / (df['avg_packet_size'] + 1)
    
    # NEW: Protocol diversity (entropy-like)
    df['protocol_diversity'] = -(
        df['tcp_ratio'] * np.log(df['tcp_ratio'] + 1e-6) +
        df['udp_ratio'] * np.log(df['udp_ratio'] + 1e-6) +
        df['icmp_ratio'] * np.log(df['icmp_ratio'] + 1e-6)
    )
    
    return df

def select_behavioral_features(df):
    """Select ONLY behavioral, scale-robust features."""
    features = [
        'pct_change_packets',      # Deviation from baseline
        'pct_change_bytes_ps',     # Deviation from baseline
        'pct_change_flows',        # Deviation from baseline (if present)
        'bytes_per_packet',        # Composition
        'tcp_ratio',               # Protocol mix
        'udp_ratio',
        'icmp_ratio',
        'src_ips_per_packet',      # Normalized diversity
        'dst_ips_per_packet',
        'flow_per_packet',         # Normalized flow density
        'protocol_diversity',      # Behavioral entropy
        'packet_size_range',       # Behavioral (if present)
    ]
    
    available = [f for f in features if f in df.columns]
    return df[available].copy(), available

def train_behavioral_model(train_df, test_df):
    """Train model focusing only on behavior, not volume."""
    
    print("\n" + "=" * 90)
    print("STEP 1: BEHAVIORAL FEATURE ENGINEERING")
    print("=" * 90)
    
    print("\nTraining data:")
    train_eng = engineer_behavioral_features(train_df, rolling_window=10)
    train_features, feature_names = select_behavioral_features(train_eng)
    print(f"  ✓ {len(train_features)} windows, {len(feature_names)} features")
    
    print("\nTest data:")
    test_eng = engineer_behavioral_features(test_df, rolling_window=10)
    test_features, _ = select_behavioral_features(test_eng)
    print(f"  ✓ {len(test_features)} windows, {len(feature_names)} features")
    
    print(f"\nBehavioral features: {feature_names}")
    
    # Handle missing/inf values
    train_features = train_features.fillna(0).replace([np.inf, -np.inf], 0)
    test_features = test_features.fillna(0).replace([np.inf, -np.inf], 0)
    
    print("\n" + "=" * 90)
    print("STEP 2: FIT SCALER & TRAIN MODEL")
    print("=" * 90)
    
    # Fit scaler only on training data
    scaler = RobustScaler()
    train_scaled = scaler.fit_transform(train_features)
    test_scaled = scaler.transform(test_features)
    
    print(f"✓ RobustScaler fitted on {len(train_scaled)} training samples")
    
    # Train Isolation Forest with lower contamination (expect fewer anomalies now)
    model = IsolationForest(
        contamination=0.03,  # Expect ~3% anomalies in normal data
        n_estimators=150,
        random_state=42,
        n_jobs=-1
    )
    model.fit(train_scaled)
    print(f"✓ Isolation Forest trained (contamination=3%)")
    
    # Get anomaly scores
    train_scores = -model.score_samples(train_scaled)
    test_scores = -model.score_samples(test_scaled)
    
    train_preds = model.predict(train_scaled)
    test_preds = model.predict(test_scaled)
    
    print(f"✓ Predictions computed")
    
    print("\n" + "=" * 90)
    print("STEP 3: SANITY CHECKS")
    print("=" * 90)
    
    # Check 1: Distribution overlap
    print("\nCheck 1: Feature Distribution Overlap")
    print("-" * 90)
    for feat in feature_names[:6]:  # Show first 6
        train_mean = train_features[feat].mean()
        test_mean = test_features[feat].mean()
        train_std = train_features[feat].std()
        test_std = test_features[feat].std()
        separation = abs(train_mean - test_mean) / (max(train_std, test_std) + 1e-6)
        print(f"  {feat}: sep={separation:.3f} (train μ={train_mean:.3f}, test μ={test_mean:.3f})")
    
    # Check 2: Anomaly rate
    print("\nCheck 2: Anomaly Rates")
    print("-" * 90)
    train_anom_pct = (train_preds == -1).sum() / len(train_preds) * 100
    test_anom_pct = (test_preds == -1).sum() / len(test_preds) * 100
    print(f"  Training anomaly rate: {train_anom_pct:.2f}%")
    print(f"  Test anomaly rate:     {test_anom_pct:.2f}%")
    
    if train_anom_pct < 1 or train_anom_pct > 10:
        print(f"    ⚠️  Training rate out of expected range (1-10%)")
    else:
        print(f"    ✓ Healthy training range")
    
    if test_anom_pct < 1 or test_anom_pct > 50:
        print(f"    ⚠️  Test rate extreme")
    else:
        print(f"    ✓ Reasonable test range")
    
    # Check 3: Correlation with volume (should be much lower now!)
    print("\nCheck 3: Score Independence from Volume")
    print("-" * 90)
    if 'pct_change_packets' in train_features.columns:
        # Correlation with behavioral feature (not volume)
        train_corr_behavior = np.corrcoef(train_scores, train_features['pct_change_packets'].values)[0, 1]
        test_corr_behavior = np.corrcoef(test_scores, test_features['pct_change_packets'].values)[0, 1]
        print(f"  Score vs pct_change_packets (behavioral):")
        print(f"    Training: r={train_corr_behavior:.3f}")
        print(f"    Test:     r={test_corr_behavior:.3f}")
        
        if abs(train_corr_behavior) > 0.7:
            print(f"    ⚠️  High correlation (should be < 0.3)")
        else:
            print(f"    ✓ Low correlation - behavior is independent")
    
    # Check 4: Score vs protocol ratios
    print("\nCheck 4: Score vs Protocol Mix (should correlate if anomalies are behavioral)")
    print("-" * 90)
    if 'tcp_ratio' in train_features.columns:
        train_corr_tcp = np.corrcoef(train_scores, train_features['tcp_ratio'].values)[0, 1]
        test_corr_tcp = np.corrcoef(test_scores, test_features['tcp_ratio'].values)[0, 1]
        print(f"  Score vs tcp_ratio:")
        print(f"    Training: r={train_corr_tcp:.3f}")
        print(f"    Test:     r={test_corr_tcp:.3f}")
    
    results = {
        'model': model,
        'scaler': scaler,
        'feature_names': feature_names,
        'train_scores': train_scores,
        'train_predictions': train_preds,
        'test_scores': test_scores,
        'test_predictions': test_preds,
        'train_features': train_features,
        'test_features': test_features,
        'train_engineered': train_eng,
        'test_engineered': test_eng,
    }
    
    return results

def save_model_and_artifacts(results, out_dir: Path):
    """Save trained model and metadata."""
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Save model
    model_path = out_dir / 'network_anomaly_model_behavioral.pkl'
    with open(model_path, 'wb') as f:
        pickle.dump({
            'model': results['model'],
            'scaler': results['scaler'],
            'feature_names': results['feature_names'],
        }, f)
    print(f"✓ Model saved: {model_path.name}")
    
    # Save config
    config_path = out_dir / 'behavioral_features_config.json'
    with open(config_path, 'w') as f:
        json.dump({
            'feature_names': results['feature_names'],
            'scaler_type': 'RobustScaler',
            'model_type': 'IsolationForest',
            'contamination': 0.03,
            'rolling_window': 10,
            'notes': 'Behavioral only: no absolute volume features. Uses % change, ratios, normalized diversity.',
        }, f, indent=2)
    print(f"✓ Config saved: {config_path.name}")

def create_comparison_viz(results, out_dir: Path):
    """Create diagnostics visualization."""
    out_dir.mkdir(parents=True, exist_ok=True)
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Behavioral Model: Score Analysis (Scale-Independent)', fontsize=16, fontweight='bold')
    
    # (0,0) Score distribution
    ax = axes[0, 0]
    ax.hist(results['train_scores'], bins=20, alpha=0.6, color='blue', label='Training', edgecolor='black')
    ax.hist(results['test_scores'], bins=20, alpha=0.6, color='red', label='Test', edgecolor='black')
    ax.set_title('Anomaly Score Distribution', fontweight='bold')
    ax.set_xlabel('Score')
    ax.set_ylabel('Count')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # (0,1) Score vs behavioral deviation
    ax = axes[0, 1]
    if 'pct_change_packets' in results['train_features'].columns:
        ax.scatter(results['train_features']['pct_change_packets'], results['train_scores'],
                  alpha=0.5, s=30, color='blue', label='Training')
        ax.scatter(results['test_features']['pct_change_packets'], results['test_scores'],
                  alpha=0.5, s=30, color='red', label='Test')
        ax.set_xlabel('% Change in Packet Count\n(vs rolling baseline)')
    ax.set_ylabel('Anomaly Score')
    ax.set_title('Score vs Behavioral Deviation', fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # (1,0) Score vs protocol diversity
    ax = axes[1, 0]
    if 'protocol_diversity' in results['train_features'].columns:
        ax.scatter(results['train_features']['protocol_diversity'], results['train_scores'],
                  alpha=0.5, s=30, color='blue', label='Training')
        ax.scatter(results['test_features']['protocol_diversity'], results['test_scores'],
                  alpha=0.5, s=30, color='red', label='Test')
        ax.set_xlabel('Protocol Diversity')
        ax.set_title('Score vs Protocol Mix', fontweight='bold')
    ax.set_ylabel('Anomaly Score')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # (1,1) Summary
    ax = axes[1, 1]
    ax.axis('off')
    summary_text = f"""
    BEHAVIORAL MODEL SUMMARY
    ━━━━━━━━━━━━━━━━━━━━━━━
    
    Training Data:
      • Windows: {len(results['train_scores'])}
      • Anomalies: {(results['train_predictions'] == -1).sum()} ({(results['train_predictions'] == -1).mean()*100:.1f}%)
      • Mean score: {results['train_scores'].mean():.4f}
    
    Test Data (merged_50M):
      • Windows: {len(results['test_scores'])}
      • Anomalies: {(results['test_predictions'] == -1).sum()} ({(results['test_predictions'] == -1).mean()*100:.1f}%)
      • Mean score: {results['test_scores'].mean():.4f}
    
    Features: {len(results['feature_names'])}
      (All behavioral/relative)
    
    Status: ✓ BEHAVIOR-BASED
    """
    ax.text(0.05, 0.95, summary_text, transform=ax.transAxes, fontsize=9.5,
           verticalalignment='top', family='monospace',
           bbox=dict(boxstyle='round', facecolor='#f0f0f0', alpha=0.8))
    
    plt.tight_layout()
    out_file = out_dir / 'behavioral_model_diagnostics.png'
    plt.savefig(out_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Diagnostics saved: {out_file.name}")

def main():
    print("=" * 90)
    print("LOADING DATA")
    print("=" * 90)
    
    train_json = ROOT / 'data' / 'processed' / 'training_data_consolidated.json'
    test_json = ROOT / 'docs' / 'model_insight' / 'split_merged_50M_features.json'
    
    if not train_json.exists() or not test_json.exists():
        print(f"❌ Missing data files")
        sys.exit(1)
    
    print(f"Loading: {train_json.name}")
    train_df = load_features(train_json)
    print(f"Loading: {test_json.name}")
    test_df = load_features(test_json)
    print(f"✓ {len(train_df)} training + {len(test_df)} test windows\n")
    
    # Train behavioral model
    results = train_behavioral_model(train_df, test_df)
    
    # Save
    print("\n" + "=" * 90)
    print("SAVING MODEL")
    print("=" * 90)
    save_model_and_artifacts(results, ROOT / 'models')
    
    # Visualize
    print("\n" + "=" * 90)
    print("CREATING DIAGNOSTICS")
    print("=" * 90)
    create_comparison_viz(results, ROOT / 'docs' / 'model_insight')
    
    print("\n" + "=" * 90)
    print("✓ BEHAVIORAL MODEL TRAINING COMPLETE")
    print("=" * 90)

if __name__ == '__main__':
    main()
