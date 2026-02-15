"""
Quick test of new model trained on 1,806 local capture windows.
Compare against old model trained on 91 windows.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.ml.inference import AnomalyPredictor
from scripts.data_cleanup import clean_and_engineer_features, select_features

print("\n" + "="*80)
print("MODEL COMPARISON: Old (91 windows) vs New (1,806 windows)")
print("="*80 + "\n")

# Load test data (use a subset of the training data for quick test)
test_file = Path("data/processed/local_captures/Capture_28_01_2026_features.json")

with open(test_file, 'r') as f:
    data = json.load(f)

df = pd.DataFrame(data)
print(f"Test data: {len(df)} windows from {test_file.name}\n")

# Clean
df = clean_and_engineer_features(df)
df = select_features(df)

# Test OLD model (91 windows)
try:
    print("[1] Testing OLD model (91 windows)...")
    old_predictor = AnomalyPredictor('models/network_anomaly_model.pkl')
    old_results = old_predictor.predict_and_label(df)
    old_anomalies = old_results['is_anomaly'].sum()
    old_pct = 100 * old_anomalies / len(df)
    print(f"    Anomalies detected: {old_anomalies}/{len(df)} ({old_pct:.1f}%)")
    print(f"    Score range: {old_results['score'].min():.4f} to {old_results['score'].max():.4f}")
except Exception as e:
    print(f"    ✗ Error: {e}")
    old_anomalies = None

# Test NEW model (1,806 windows)
print("\n[2] Testing NEW model (1,806 windows)...")
new_predictor = AnomalyPredictor('models/network_anomaly_model_local.pkl')
new_results = new_predictor.predict_and_label(df)
new_anomalies = new_results['is_anomaly'].sum()
new_pct = 100 * new_anomalies / len(df)
print(f"    Anomalies detected: {new_anomalies}/{len(df)} ({new_pct:.1f}%)")
print(f"    Score range: {new_results['score'].min():.4f} to {new_results['score'].max():.4f}")

# Comparison
if old_anomalies is not None:
    print("\n" + "="*80)
    print("COMPARISON")
    print("="*80)
    print(f"Old model: {old_pct:.1f}% flagged as anomalies")
    print(f"New model: {new_pct:.1f}% flagged as anomalies")
    
    if old_pct > 90 and new_pct < 50:
        print("\n✅ SIGNIFICANT IMPROVEMENT!")
        print("   Old model was overfitted (flagged everything)")
        print("   New model shows more realistic detection rates")
    elif abs(old_pct - new_pct) < 10:
        print("\n⚠️  Similar detection rates")
        print("   May need more diverse data (normal + attack samples)")
    
print("\n" + "="*80)
print(f"Next steps:")
print(f"  • Add enterprise captures when available")
print(f"  • Acquire labeled attack samples for validation")
print(f"  • Use new model: update inference.py to load 'network_anomaly_model_local.pkl'")
print("="*80 + "\n")
