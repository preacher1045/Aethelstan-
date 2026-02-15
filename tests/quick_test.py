"""
Quick anomaly detection test on new PCAP data
"""
import json
import pandas as pd
from backend.ml.inference import AnomalyPredictor
from scripts.data_cleanup import clean_and_engineer_features, select_features

print("\n" + "="*70)
print("ANOMALY DETECTION ON test_net_traffic.pcapng")
print("="*70)

# Load features
print("\n📂 Loading extracted features...")
with open('data/processed/test_net_traffic_features.json', 'r') as f:
    features = json.load(f)

df = pd.DataFrame(features)
print(f"   Loaded {len(df)} windows")

# Clean and engineer features
print("\n🧹 Cleaning and engineering features...")
df = clean_and_engineer_features(df)
df = select_features(df)
print(f"   Final feature shape: {df.shape}")

# Load model and predict
print("\n🤖 Running anomaly detection...")
predictor = AnomalyPredictor('models/network_anomaly_model.pkl')
results = predictor.predict_from_features(df)

# Display results
print("\n" + "="*70)
print("RESULTS")
print("="*70)
print(f"Total windows analyzed: {len(df)}")
print(f"Anomalies detected: {results['anomaly_count']}")
print(f"Anomaly ratio: {results['anomaly_ratio']:.2%}")
print(f"Mean anomaly score: {results['scores'].mean():.4f}")
print("="*70)

# Show detailed breakdown
labeled_df = predictor.predict_and_label(df)

print("\n📊 Detailed Breakdown:")
print("-"*70)
for idx, row in labeled_df.iterrows():
    status = "🚨 ANOMALY" if row['is_anomaly'] else "✅ Normal"
    print(f"Window {idx+1}: {status}")
    print(f"  Score: {row['score']:.4f}")
    print(f"  Packets: {row['packet_count']:,}")
    print(f"  Bytes/sec: {row['bytes_per_sec']:,.0f}")
    print(f"  TCP: {row['tcp_ratio']:.1%} | UDP: {row['udp_ratio']:.1%} | ICMP: {row['icmp_ratio']:.1%}")
    print()

print("="*70)
print("✅ SYSTEM TEST COMPLETE - ALL COMPONENTS WORKING!")
print("="*70)
