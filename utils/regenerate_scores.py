"""Regenerate anomaly scores from model inference"""
import json
import pickle
import pandas as pd
import numpy as np
from pathlib import Path
from backend.ml.inference import AnomalyPredictor
from scripts.data_cleanup import clean_and_engineer_features, select_features, normalize_features

# Load features
features_file = "data/processed/2023_test_features.json"
print(f"Loading features from {features_file}")
with open(features_file, 'r') as f:
    features = json.load(f)

df = pd.DataFrame(features)
print(f"Loaded {len(df)} windows")

# Clean & engineer
print("Cleaning and engineering features...")
df = clean_and_engineer_features(df)
df = select_features(df)
print(f"After cleaning: {df.shape}")

# Load model & predict
print("Loading model...")
predictor = AnomalyPredictor('models/network_anomaly_model.pkl')
predictions_df = predictor.predict_and_label(df)

# Extract scores
anomaly_scores = predictions_df['score'].values
anomaly_flags = predictions_df['is_anomaly'].values.astype(int)

print(f"Score range: {anomaly_scores.min():.4f} to {anomaly_scores.max():.4f}")
print(f"Anomalies flagged: {anomaly_flags.sum()}/{len(anomaly_flags)}")

# Save scores for baseline test
scores_data = {
    'window_ids': list(range(len(anomaly_scores))),
    'anomaly_scores': anomaly_scores.tolist(),
    'anomaly_flags': anomaly_flags.tolist()
}

with open('data/processed/2023_anomaly_scores.json', 'w') as f:
    json.dump(scores_data, f)

print("\n✓ Scores saved to data/processed/2023_anomaly_scores.json")
