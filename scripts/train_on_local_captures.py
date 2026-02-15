"""
Simple training workflow for local captures.
Run this AFTER all feature extraction is complete.
"""

import json
import pandas as pd
from pathlib import Path
import sys

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.data_cleanup import clean_and_engineer_features, select_features
from backend.ml.model import AnomalyDetector

def main():
    base_dir = Path(__file__).parent.parent
    
    print("\n" + "="*80)
    print("TRAINING MODEL ON LOCAL CAPTURES")
    print("="*80 + "\n")
    
    # Step 1: Load and combine all local capture features
    features_dir = base_dir / "data" / "processed" / "local_captures"
    feature_files = list(features_dir.glob("*_features.json"))
    
    if not feature_files:
        print(f"❌ No feature files found in {features_dir}")
        print("Run feature extraction first!")
        return
    
    print(f"Found {len(feature_files)} feature files:")
    all_dfs = []
    
    for f in sorted(feature_files):
        with open(f, 'r') as file:
            data = json.load(file)
        
        df = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])
        df['source_file'] = f.stem.replace('_features', '')
        
        print(f"  • {f.name}: {len(df)} windows")
        all_dfs.append(df)
    
    # Combine
    combined_df = pd.concat(all_dfs, ignore_index=True)
    print(f"\n✓ Total windows combined: {len(combined_df)}")
    
    # Step 2: Clean and engineer features
    print("\nCleaning and engineering features...")
    combined_df = clean_and_engineer_features(combined_df)
    combined_df = select_features(combined_df)
    print(f"✓ Final feature shape: {combined_df.shape}")
    
    # Step 3: Train model
    print("\nTraining model...")
    model = AnomalyDetector(contamination=0.05)  # 5% expected anomalies
    model.fit(combined_df)
    
    # Step 4: Save model
    model_path = base_dir / "models" / "network_anomaly_model_local.pkl"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(model_path))
    
    print(f"\n✓ Model trained and saved to: {model_path}")
    
    # Step 5: Save combined training data
    training_data_path = base_dir / "data" / "training" / "local_captures_combined.json"
    training_data_path.parent.mkdir(parents=True, exist_ok=True)
    combined_df.to_json(training_data_path, orient='records')
    
    print(f"✓ Training data saved to: {training_data_path}")
    
    print("\n" + "="*80)
    print("TRAINING COMPLETE!")
    print("="*80)
    print(f"\nModel stats:")
    print(f"  Training samples: {len(combined_df)}")
    print(f"  Features: {combined_df.shape[1]}")
    print(f"  Sources: {', '.join(df['source_file'].unique() if 'source_file' in combined_df.columns else ['unknown'])}")
    print(f"\nNext steps:")
    print(f"  1. Test model: python test_inference.py")
    print(f"  2. Add more data when available")
    print(f"  3. Retrain: python scripts/train_on_local_captures.py")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
