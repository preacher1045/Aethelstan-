"""
Train model on ALL available data: local captures + enterprise PCAPs.
Combines multiple data sources for robust anomaly detection.
"""

import json
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.data_cleanup import clean_and_engineer_features, select_features
from backend.ml.model import AnomalyDetector

def load_features_from_directory(feature_dir: Path, dataset_name: str):
    """Load all feature files from a directory."""
    feature_files = list(feature_dir.glob("*_features.json"))
    
    if not feature_files:
        return None
    
    print(f"\n{dataset_name}:")
    all_dfs = []
    
    for f in sorted(feature_files):
        with open(f, 'r') as file:
            data = json.load(file)
        
        df = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])
        df['source_file'] = f.stem.replace('_features', '')
        df['dataset'] = dataset_name
        
        print(f"  • {f.name}: {len(df)} windows")
        all_dfs.append(df)
    
    combined = pd.concat(all_dfs, ignore_index=True)
    print(f"  ✓ Subtotal: {len(combined)} windows")
    
    return combined

def main():
    base_dir = Path(__file__).parent.parent
    
    print("\n" + "="*80)
    print("TRAINING MODEL ON ALL DATA (LOCAL + ENTERPRISE)")
    print("="*80)
    
    # Load local captures
    local_dir = base_dir / "data" / "processed" / "local_captures"
    local_df = load_features_from_directory(local_dir, "local_captures")
    
    # Load enterprise captures
    enterprise_dir = base_dir / "data" / "processed" / "enterprise_pcap_files"
    enterprise_df = load_features_from_directory(enterprise_dir, "enterprise")
    
    # Combine all datasets
    datasets = [df for df in [local_df, enterprise_df] if df is not None]
    
    if not datasets:
        print("\n❌ No feature files found!")
        print("Run feature extraction first:")
        print("  python scripts\\batch_extract_features.py")
        return
    
    combined_df = pd.concat(datasets, ignore_index=True)
    
    print("\n" + "-"*80)
    print(f"COMBINED TOTAL: {len(combined_df)} windows")
    print("-"*80)
    
    # Show dataset distribution
    print("\nDataset distribution:")
    for dataset in combined_df['dataset'].unique():
        count = (combined_df['dataset'] == dataset).sum()
        pct = 100 * count / len(combined_df)
        print(f"  {dataset}: {count} windows ({pct:.1f}%)")
    
    # Clean and engineer features
    print("\nCleaning and engineering features...")
    combined_df = clean_and_engineer_features(combined_df)
    combined_df = select_features(combined_df)
    print(f"✓ Final feature shape: {combined_df.shape}")
    
    # Train model
    print(f"\nTraining model on {len(combined_df)} windows...")
    print("(This may take several minutes for large datasets)")
    
    contamination = 0.05  # 5% expected anomalies
    model = AnomalyDetector(contamination=contamination)
    model.fit(combined_df)
    
    # Save model
    model_path = base_dir / "models" / "network_anomaly_model_combined.pkl"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(model_path))
    
    print(f"\n✓ Model trained and saved to: {model_path}")
    
    # Save combined training data
    training_data_path = base_dir / "data" / "training" / "all_data_combined.json"
    training_data_path.parent.mkdir(parents=True, exist_ok=True)
    combined_df.to_json(training_data_path, orient='records')
    
    print(f"✓ Training data saved to: {training_data_path}")
    
    # Summary
    print("\n" + "="*80)
    print("TRAINING COMPLETE!")
    print("="*80)
    print(f"\nModel stats:")
    print(f"  Training samples: {len(combined_df)}")
    print(f"  Features: {len(feature_cols)}")
    print(f"  Contamination: {contamination} ({int(contamination*100)}%)")
    print(f"  Datasets combined: {len(dataset_dirs)}")
    
    print(f"\nDataset breakdown:")
    for name, path in dataset_dirs.items():
        count = stats[name]['total_windows']
        print(f"  • {name}: {count} windows")
    
    print(f"\nNext steps:")
    print(f"  1. Test model: python test_new_model.py")
    print(f"  2. Compare with previous models")
    print(f"  3. Use in production: update inference to load 'network_anomaly_model_combined.pkl'")
    print(f"  4. Acquire labeled attack samples for validation")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
