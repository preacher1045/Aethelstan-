"""
Quick test of inference on trained model
"""
import json
import pandas as pd
from backend.ml.inference import AnomalyPredictor
from scripts.data_cleanup import load_rust_output, clean_and_engineer_features, select_features

# Load and clean data first
print("\nLoading and cleaning data...")
df = load_rust_output('data/processed/window_features.json')
df = clean_and_engineer_features(df)
df = select_features(df)

# Load predictor
print("Loading model...")
predictor = AnomalyPredictor('models/network_anomaly_model.pkl')

# Make predictions
print("Running inference...")
results = predictor.predict_from_features(df)

print("\n" + "="*60)
print("INFERENCE RESULTS")
print("="*60)
print(f"Total samples: {len(df)}")
print(f"Anomalies detected: {results['anomaly_count']}")
print(f"Anomaly ratio: {results['anomaly_ratio']:.2%}")
print("="*60)

# Show top anomalies
labeled_df = predictor.predict_and_label(df)
top_5 = predictor.get_top_anomalies(df, top_n=5)
print("\nTop 5 Most Anomalous Windows:")
print(top_5[['packet_count', 'total_bytes', 'tcp_ratio', 'score', 'is_anomaly']].to_string())
print()
