"""Compare all trained models on the same test data."""
import json
import sys
from pathlib import Path
import pickle
import pandas as pd
import numpy as np

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from backend.ml.model import AnomalyDetector
from data_cleanup import clean_and_engineer_features, select_features

def load_test_data(test_file_path):
    """Load test data from JSON file."""
    with open(test_file_path, 'r') as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        data = [data]
    
    df = pd.DataFrame(data)
    return df

def compare_models(test_file):
    """Compare all available models."""
    base_dir = Path(__file__).parent.parent
    models_dir = base_dir / "models"
    
    # Models to compare
    models = {
        "Original (91 windows)": models_dir / "network_anomaly_model.pkl",
        "Local Only (1,806 windows)": models_dir / "network_anomaly_model_local.pkl",
        "Combined (1,988 windows)": models_dir / "network_anomaly_model_combined.pkl"
    }
    
    # Load test data
    print("="*80)
    print("MODEL COMPARISON")
    print("="*80)
    print(f"\nTest file: {test_file}")
    
    df = load_test_data(test_file)
    
    # Use same feature engineering as training
    df_engineered = clean_and_engineer_features(df)
    X_test = select_features(df_engineered)
    
    print(f"Test samples: {len(X_test)}")
    print(f"Features: {X_test.shape[1]}")
    print("\n" + "-"*80)
    
    results = {}
    
    for name, model_path in models.items():
        if not model_path.exists():
            print(f"\n{name}:")
            print(f"  ⚠️ Model not found: {model_path.name}")
            continue
        
        # Load model
        with open(model_path, 'rb') as f:
            model_obj = pickle.load(f)
        
        # Handle different model formats (dict vs AnomalyDetector object)
        if isinstance(model_obj, dict):
            # Old format: {'model': ..., 'scaler': ..., 'feature_names': ...}
            scaler = model_obj['scaler']
            model = model_obj['model']
            X_scaled = scaler.transform(X_test)
            predictions = model.predict(X_scaled)
            scores = model.score_samples(X_scaled)
        else:
            # New format: AnomalyDetector object
            model = model_obj
            predictions = model.predict(X_test)
            scores = model.predict_anomaly_score(X_test)
        
        # Calculate stats
        anomaly_count = (predictions == -1).sum()
        anomaly_rate = (anomaly_count / len(predictions)) * 100
        
        results[name] = {
            'anomaly_count': anomaly_count,
            'anomaly_rate': anomaly_rate,
            'avg_score': scores.mean(),
            'min_score': scores.min(),
            'max_score': scores.max()
        }
        
        print(f"\n{name}:")
        print(f"  Anomalies detected: {anomaly_count}/{len(predictions)} ({anomaly_rate:.1f}%)")
        print(f"  Avg anomaly score: {scores.mean():.3f}")
        print(f"  Score range: [{scores.min():.3f}, {scores.max():.3f}]")
    
    # Summary comparison
    print("\n" + "="*80)
    print("COMPARISON SUMMARY")
    print("="*80)
    
    if len(results) >= 2:
        print("\nAnomaly Detection Rate:")
        for name, stats in results.items():
            bar = "█" * int(stats['anomaly_rate'])
            print(f"  {name:<30} {stats['anomaly_rate']:>5.1f}% {bar}")
        
        print("\nKey Insights:")
        
        # Compare original vs local
        if "Original (91 windows)" in results and "Local Only (1,806 windows)" in results:
            orig_rate = results["Original (91 windows)"]['anomaly_rate']
            local_rate = results["Local Only (1,806 windows)"]['anomaly_rate']
            improvement = orig_rate - local_rate
            print(f"  • Original → Local: {improvement:+.1f}% change ({orig_rate:.1f}% → {local_rate:.1f}%)")
        
        # Compare local vs combined
        if "Local Only (1,806 windows)" in results and "Combined (1,988 windows)" in results:
            local_rate = results["Local Only (1,806 windows)"]['anomaly_rate']
            combined_rate = results["Combined (1,988 windows)"]['anomaly_rate']
            diff = combined_rate - local_rate
            print(f"  • Local → Combined: {diff:+.1f}% change ({local_rate:.1f}% → {combined_rate:.1f}%)")
            
            if abs(diff) < 1:
                print(f"    → Similar performance (enterprise data added minimal value)")
            elif diff < 0:
                print(f"    → Slight improvement (fewer false positives)")
            else:
                print(f"    → Slightly more sensitive (more detections)")
    
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    # Use a subset of test data for quick comparison
    test_file = Path(__file__).parent.parent / "data" / "processed" / "local_captures" / "Capture_28_01_2026_features.json"
    
    if not test_file.exists():
        print(f"Error: Test file not found: {test_file}")
        sys.exit(1)
    
    compare_models(test_file)
