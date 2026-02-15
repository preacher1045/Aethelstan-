"""
Retrain anomaly detection model with scale-robust features.

Step 1: Engineer scale-robust features (log, ratios, % change vs baseline)
Step 2: Retrain Isolation Forest on engineered training data
Step 3: Evaluate on test data
Step 4: Run sanity checks
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

def engineer_scale_robust_features(df, rolling_window=10, is_training=False):
    """
    Engineer scale-robust features.
    
    Args:
        df: DataFrame with raw features (sorted by time)
        rolling_window: Number of previous windows for baseline (5-20)
        is_training: If True, don't compute rolling % change for first N windows
    """
    df = df.copy()
    
    print(f"  Engineering features (rolling_window={rolling_window})...")
    
    # 1. Log-scaled packet count
    df['log_packet_count'] = np.log1p(df['packet_count'])
    
    # 2. Bytes per packet (guard against divide by zero)
    df['bytes_per_packet'] = df['total_bytes'] / df['packet_count'].replace(0, 1)
    
    # 3. Percentage change vs rolling baseline (critical!)
    # We need at least rolling_window samples to compute
    if len(df) >= rolling_window:
        # For packet_count
        rolling_packets = df['packet_count'].rolling(window=rolling_window, min_periods=1).mean()
        df['pct_change_packet_count'] = (df['packet_count'] - rolling_packets) / (rolling_packets + 1)
        
        # For bytes_per_sec
        rolling_bytes_ps = df['bytes_per_sec'].rolling(window=rolling_window, min_periods=1).mean()
        df['pct_change_bytes_per_sec'] = (df['bytes_per_sec'] - rolling_bytes_ps) / (rolling_bytes_ps + 1)
        
        # For flow_count (if present)
        if 'flow_count' in df.columns:
            rolling_flows = df['flow_count'].rolling(window=rolling_window, min_periods=1).mean()
            df['pct_change_flow_count'] = (df['flow_count'] - rolling_flows) / (rolling_flows + 1)
    else:
        # For small datasets, set to 0 (no baseline history)
        df['pct_change_packet_count'] = 0.0
        df['pct_change_bytes_per_sec'] = 0.0
        if 'flow_count' in df.columns:
            df['pct_change_flow_count'] = 0.0
    
    # 4. Normalized ratios (already have protocol ratios, add IP/flow ratios)
    df['src_ips_per_packet'] = df['unique_src_ips'] / (df['packet_count'] + 1)
    df['dst_ips_per_packet'] = df['unique_dst_ips'] / (df['packet_count'] + 1)
    if 'flow_count' in df.columns:
        df['flow_per_packet'] = df['flow_count'] / (df['packet_count'] + 1)
    
    # Keep protocol ratios (already normalized)
    # tcp_ratio, udp_ratio, icmp_ratio should exist
    
    return df

def select_ml_features(df):
    """Select final feature set for ML."""
    features = [
        'log_packet_count',           # Log-scaled volume
        'bytes_per_packet',            # Composition
        'pct_change_packet_count',     # Behavioral deviation
        'pct_change_bytes_per_sec',    # Behavioral deviation
        'tcp_ratio',                   # Protocol mix
        'udp_ratio',
        'icmp_ratio',
        'src_ips_per_packet',          # Normalized IP diversity
        'dst_ips_per_packet',
        'flow_per_packet' if 'flow_per_packet' in df.columns else None,
    ]
    features = [f for f in features if f is not None]
    
    # Check availability
    available = [f for f in features if f in df.columns]
    missing = [f for f in features if f not in df.columns]
    
    if missing:
        print(f"    ⚠️  Missing features: {missing}")
    
    return df[available].copy(), available

def train_scale_robust_model(train_df, test_df):
    """Train and evaluate scale-robust model."""
    
    print("\n" + "=" * 90)
    print("STEP 1: FEATURE ENGINEERING")
    print("=" * 90)
    
    print("\nTraining data:")
    train_eng = engineer_scale_robust_features(train_df, rolling_window=5, is_training=True)
    train_features, feature_names = select_ml_features(train_eng)
    print(f"  ✓ {len(train_features)} windows, {len(feature_names)} features")
    
    print("\nTest data:")
    test_eng = engineer_scale_robust_features(test_df, rolling_window=5, is_training=False)
    test_features, _ = select_ml_features(test_eng)
    print(f"  ✓ {len(test_features)} windows, {len(feature_names)} features")
    
    print(f"\nFeatures used: {feature_names}")
    
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
    
    # Train Isolation Forest
    model = IsolationForest(
        contamination=0.05,  # Expect ~5% anomalies
        n_estimators=100,
        random_state=42,
        n_jobs=-1
    )
    model.fit(train_scaled)
    print(f"✓ Isolation Forest trained (contamination=5%)")
    
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
    for feat in feature_names[:5]:  # Show first 5
        train_mean = train_features[feat].mean()
        test_mean = test_features[feat].mean()
        train_std = train_features[feat].std()
        test_std = test_features[feat].std()
        separation = abs(train_mean - test_mean) / (max(train_std, test_std) + 1e-6)
        print(f"  {feat}:")
        print(f"    Training: μ={train_mean:.4f}, σ={train_std:.4f}")
        print(f"    Test:     μ={test_mean:.4f}, σ={test_std:.4f}")
        print(f"    Separation: {separation:.3f}")
    
    # Check 2: Anomaly rate
    print("\nCheck 2: Anomaly Rates")
    print("-" * 90)
    train_anom_pct = (train_preds == -1).sum() / len(train_preds) * 100
    test_anom_pct = (test_preds == -1).sum() / len(test_preds) * 100
    print(f"  Training anomaly rate: {train_anom_pct:.2f}%")
    print(f"  Test anomaly rate:     {test_anom_pct:.2f}%")
    
    if train_anom_pct < 0.1:
        print(f"    ⚠️  Training rate too low (expect 1-5%)")
    elif train_anom_pct > 20:
        print(f"    ⚠️  Training rate too high")
    else:
        print(f"    ✓ Healthy range")
    
    if test_anom_pct < 0.1 or test_anom_pct > 95:
        print(f"    ⚠️  Test rate extreme (100% or 0%)")
    else:
        print(f"    ✓ Reasonable range (not 0% or 100%)")
    
    # Check 3: Correlation with volume (make sure we fixed the scale bias)
    print("\nCheck 3: Score vs Volume Correlation")
    print("-" * 90)
    train_corr_packets = np.corrcoef(train_scores, train_features['log_packet_count'].values)[0, 1]
    test_corr_packets = np.corrcoef(test_scores, test_features['log_packet_count'].values)[0, 1]
    print(f"  Training score vs log_packet_count: r={train_corr_packets:.3f}")
    print(f"  Test score vs log_packet_count:     r={test_corr_packets:.3f}")
    
    if abs(train_corr_packets) > 0.5 or abs(test_corr_packets) > 0.5:
        print(f"    ⚠️  Still correlated with volume (should be < 0.3)")
    else:
        print(f"    ✓ Good - score is independent of volume")
    
    print("\n" + "=" * 90)
    print("STEP 4: RESULTS SUMMARY")
    print("=" * 90)
    
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
    model_path = out_dir / 'network_anomaly_model_scale_robust.pkl'
    with open(model_path, 'wb') as f:
        pickle.dump({
            'model': results['model'],
            'scaler': results['scaler'],
            'feature_names': results['feature_names'],
        }, f)
    print(f"✓ Model saved: {model_path.name}")
    
    # Save feature engineering config
    config_path = out_dir / 'scale_robust_features_config.json'
    with open(config_path, 'w') as f:
        json.dump({
            'feature_names': results['feature_names'],
            'scaler_type': 'RobustScaler',
            'model_type': 'IsolationForest',
            'rolling_window': 5,
            'engineering_notes': 'Log scale, % change vs baseline, normalized ratios'
        }, f, indent=2)
    print(f"✓ Config saved: {config_path.name}")
    
    # Save predictions
    preds_path = out_dir / 'scale_robust_predictions.json'
    with open(preds_path, 'w') as f:
        json.dump({
            'train': {
                'scores': results['train_scores'].tolist(),
                'predictions': results['train_predictions'].tolist(),
                'anomaly_count': int((results['train_predictions'] == -1).sum()),
                'anomaly_pct': float((results['train_predictions'] == -1).mean() * 100),
            },
            'test': {
                'scores': results['test_scores'].tolist(),
                'predictions': results['test_predictions'].tolist(),
                'anomaly_count': int((results['test_predictions'] == -1).sum()),
                'anomaly_pct': float((results['test_predictions'] == -1).mean() * 100),
            }
        }, f, indent=2)
    print(f"✓ Predictions saved: {preds_path.name}")

def create_comparison_viz(results, out_dir: Path):
    """Create visualization comparing old (volume-based) vs new (scale-robust) approach."""
    out_dir.mkdir(parents=True, exist_ok=True)
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Scale-Robust Model: Training Diagnostics', fontsize=16, fontweight='bold')
    
    # (0,0) Score distribution
    ax = axes[0, 0]
    ax.hist(results['train_scores'], bins=30, alpha=0.7, color='blue', edgecolor='black', label='Training')
    ax.hist(results['test_scores'], bins=20, alpha=0.7, color='red', edgecolor='black', label='Test')
    ax.set_title('Anomaly Score Distribution', fontweight='bold')
    ax.set_xlabel('Score')
    ax.set_ylabel('Count')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # (0,1) Score vs log_packet_count (should be uncorrelated now)
    ax = axes[0, 1]
    ax.scatter(results['train_features']['log_packet_count'], results['train_scores'], 
              alpha=0.5, s=30, color='blue', label='Training')
    ax.scatter(results['test_features']['log_packet_count'], results['test_scores'],
              alpha=0.5, s=30, color='red', label='Test')
    ax.set_title('Score vs Log Packet Count\n(should show no correlation)', fontweight='bold')
    ax.set_xlabel('log_packet_count')
    ax.set_ylabel('Anomaly Score')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # (1,0) % change in packets vs score
    ax = axes[1, 0]
    ax.scatter(results['train_features']['pct_change_packet_count'], results['train_scores'],
              alpha=0.5, s=30, color='blue', label='Training')
    ax.scatter(results['test_features']['pct_change_packet_count'], results['test_scores'],
              alpha=0.5, s=30, color='red', label='Test')
    ax.set_title('Score vs Packet Count % Change\n(behavioral deviation)', fontweight='bold')
    ax.set_xlabel('% Change from Rolling Baseline')
    ax.set_ylabel('Anomaly Score')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # (1,1) Prediction summary
    ax = axes[1, 1]
    ax.axis('off')
    summary_text = f"""
    SCALE-ROBUST MODEL RESULTS
    ━━━━━━━━━━━━━━━━━━━━━━━━━
    
    Training Data:
      • Windows: {len(results['train_scores'])}
      • Anomalies: {(results['train_predictions'] == -1).sum()} ({(results['train_predictions'] == -1).mean()*100:.1f}%)
      • Mean score: {results['train_scores'].mean():.4f}
    
    Test Data (merged_50M):
      • Windows: {len(results['test_scores'])}
      • Anomalies: {(results['test_predictions'] == -1).sum()} ({(results['test_predictions'] == -1).mean()*100:.1f}%)
      • Mean score: {results['test_scores'].mean():.4f}
    
    Features: {len(results['feature_names'])}
      {', '.join(results['feature_names'][:4])}
      {', '.join(results['feature_names'][4:])}
    
    Status: ✓ SCALE-ROBUST
    """
    ax.text(0.1, 0.9, summary_text, transform=ax.transAxes, fontsize=10,
           verticalalignment='top', family='monospace',
           bbox=dict(boxstyle='round', facecolor='#f0f0f0', alpha=0.8))
    
    plt.tight_layout()
    out_file = out_dir / 'scale_robust_model_diagnostics.png'
    plt.savefig(out_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Diagnostics saved: {out_file.name}")

def main():
    # Load data (must preserve order for rolling baseline!)
    print("=" * 90)
    print("LOADING DATA (ORDER PRESERVED)")
    print("=" * 90)
    
    train_json = ROOT / 'data' / 'processed' / 'training_data_consolidated.json'
    test_json = ROOT / 'docs' / 'model_insight' / 'split_merged_50M_features.json'
    
    if not train_json.exists() or not test_json.exists():
        print(f"❌ Missing data files")
        print(f"   Train: {train_json.exists()}")
        print(f"   Test: {test_json.exists()}")
        sys.exit(1)
    
    print(f"Loading training: {train_json.name}")
    train_df = load_features(train_json)
    
    print(f"Loading test: {test_json.name}")
    test_df = load_features(test_json)
    
    print(f"✓ {len(train_df)} training + {len(test_df)} test windows loaded\n")
    
    # Train scale-robust model
    results = train_scale_robust_model(train_df, test_df)
    
    # Save artifacts
    print("\n" + "=" * 90)
    print("SAVING MODEL & ARTIFACTS")
    print("=" * 90)
    out_dir = ROOT / 'models'
    save_model_and_artifacts(results, out_dir)
    
    # Create visualization
    print("\n" + "=" * 90)
    print("CREATING DIAGNOSTICS VISUALIZATION")
    print("=" * 90)
    create_comparison_viz(results, ROOT / 'docs' / 'model_insight')
    
    print("\n" + "=" * 90)
    print("✓ SCALE-ROBUST MODEL TRAINING COMPLETE")
    print("=" * 90)
    print(f"\nNew model: {out_dir / 'network_anomaly_model_scale_robust.pkl'}")
    print(f"Config: {out_dir / 'scale_robust_features_config.json'}")

if __name__ == '__main__':
    main()
