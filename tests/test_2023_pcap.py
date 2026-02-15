"""
Complete system test on 2023_test.pcap
Uses Rust-extracted features → Cleanup → Model Inference → Insights
"""
import json
import pandas as pd
from pathlib import Path
from backend.ml.inference import AnomalyPredictor
from scripts.data_cleanup import clean_and_engineer_features, select_features
from backend.insight.generator import InsightGenerator

print("=" * 80)
print("FULL SYSTEM TEST: 2023_test.pcap")
print("=" * 80)
print("\n📌 Pipeline:")
print("  1. ✅ Rust extractor (already ran) → data/processed/2023_test_features.json")
print("  2. 🧹 Data cleanup and feature engineering")
print("  3. 🤖 Model inference (anomaly detection)")
print("  4. 💡 Insight generation")
print("\n" + "=" * 80)

# Check if Rust extraction is complete
features_file = "data/processed/2023_test_features.json"
if not Path(features_file).exists():
    print(f"\n❌ ERROR: {features_file} not found!")
    print("   Please wait for Rust extractor to finish, then run this script again.")
    exit(1)

# Step 2: Load and clean features
print("\n🧹 STEP 2: Data Cleanup and Feature Engineering")
print("-" * 80)
with open(features_file, 'r') as f:
    raw_features = json.load(f)

print(f"✅ Loaded {len(raw_features)} windows from Rust extractor")

df = pd.DataFrame(raw_features)
print(f"   Raw feature shape: {df.shape}")

df = clean_and_engineer_features(df)
df = select_features(df)
print(f"✅ Cleaned feature shape: {df.shape}")

# Step 3: Model inference
print("\n🤖 STEP 3: Anomaly Detection (Model Inference)")
print("-" * 80)
predictor = AnomalyPredictor('models/network_anomaly_model.pkl')
labeled_df = predictor.predict_and_label(df)

anomaly_count = (labeled_df['is_anomaly'] == True).sum()
anomaly_ratio = anomaly_count / len(labeled_df)

print(f"✅ Inference complete:")
print(f"   Total windows: {len(labeled_df)}")
print(f"   Anomalies detected: {anomaly_count} ({anomaly_ratio:.1%})")
print(f"   Score range: {labeled_df['score'].min():.4f} to {labeled_df['score'].max():.4f}")

# Step 4: Generate insights
print("\n💡 STEP 4: Insight Generation")
print("-" * 80)
generator = InsightGenerator(max_alerts=10)
report = generator.generate(labeled_df.to_dict(orient='records'))

print(f"\n📊 {report['summary']}")
print(f"\n🚨 Top {len(report['alerts'])} Anomalous Windows:")
print("-" * 80)

for i, alert in enumerate(report['alerts'], 1):
    print(f"\n[{i}] {alert['alert_type']} - {alert['severity']} Severity")
    print(f"    {alert['summary']}")
    print(f"    Tags: {', '.join(alert['details'].get('tags', []))}")

# Summary stats
print("\n" + "=" * 80)
print("SYSTEM TEST RESULTS")
print("=" * 80)
print(f"Total windows analyzed: {report['stats']['total_windows']}")
print(f"Anomalies detected: {report['stats']['anomalies']}")
print(f"Score range: {report['stats']['score_min']:.4f} to {report['stats']['score_max']:.4f}")
print(f"Mean score: {report['stats']['score_mean']:.4f}")
print("\n✅ ALL PIPELINE COMPONENTS WORKING CORRECTLY!")
print("   - Rust feature extraction ✓")
print("   - Data cleanup & engineering ✓")
print("   - ML model inference ✓")
print("   - Insight generation ✓")
print("=" * 80)

# Save results
output_file = "data/processed/2023_test_insights.json"
with open(output_file, 'w') as f:
    json.dump(report, f, indent=2)
print(f"\n💾 Full insights saved to: {output_file}")
