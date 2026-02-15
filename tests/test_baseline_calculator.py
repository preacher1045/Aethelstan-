"""
Test baseline calculator with existing 91-window dataset.
Critical validation: shows if model is overfitting vs detecting real anomalies.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from scripts.baseline_calculator import BaselineCalculator

# Load existing features
features_file = Path("data/processed/2023_test_features.json")
scores_file = Path("data/processed/2023_anomaly_scores.json")

print("="*80)
print("BASELINE CALCULATOR TEST - Using Existing 91-Window Dataset")
print("="*80)

# Load features
print("\n[1] Loading feature data...")
with open(features_file, 'r') as f:
    features = json.load(f)

features_df = pd.DataFrame(features)
print(f"✓ Loaded {len(features_df)} windows with {len(features_df.columns)} columns")

# Load model predictions
print("\n[2] Loading model predictions...")
with open(scores_file, 'r') as f:
    scores_data = json.load(f)

predictions = np.array(scores_data['anomaly_scores'])
anomaly_flags = np.array(scores_data['anomaly_flags'])
print(f"✓ Loaded {len(predictions)} anomaly scores")
print(f"  Min score: {predictions.min():.4f}")
print(f"  Max score: {predictions.max():.4f}")
print(f"  Mean score: {predictions.mean():.4f}")

# Add predictions to dataframe
features_df['anomaly_score'] = predictions
features_df['predicted_anomaly'] = anomaly_flags.astype(int)

print(f"✓ {features_df['predicted_anomaly'].sum()} windows flagged as anomalies ({100*features_df['predicted_anomaly'].mean():.1f}%)")

# Calculate baseline from ALL data (treat as single traffic profile)
print("\n[3] Calculating baseline from all 91 windows...")
calculator = BaselineCalculator()
baseline = calculator.calculate_baseline(
    df=features_df,
    baseline_name="2023_all_traffic",
    exclude_columns=['window_id', 'timestamp', 'predicted_anomaly']
)
print(f"✓ Baseline computed for {len(baseline.features)} features")

# Print baseline
calculator.print_baseline("2023_all_traffic")

# Calculate baseline ONLY from "normal" windows (predicted_anomaly=0)
if features_df['predicted_anomaly'].min() == 0:
    print("\n[4] Calculating baseline from only 'normal' (non-flagged) windows...")
    normal_df = features_df[features_df['predicted_anomaly'] == 0].copy()
    
    baseline_normal = calculator.calculate_baseline(
        df=normal_df,
        baseline_name="2023_normal_only",
        exclude_columns=['window_id', 'timestamp', 'predicted_anomaly']
    )
    print(f"✓ Normal baseline computed from {len(normal_df)} windows")
    calculator.print_baseline("2023_normal_only")
    
    # Compare baseline statistics
    print("\n[5] Comparing baselines (All vs Normal-Only)...")
    print("-"*80)
    print(f"{'Feature':<30} {'All_Mean':>12} {'Normal_Mean':>12} {'Difference':>12}")
    print("-"*80)
    
    for feature in sorted(baseline.features.keys())[:10]:  # Show first 10
        all_mean = baseline.features[feature]['mean']
        normal_mean = baseline_normal.features[feature]['mean']
        diff = abs(all_mean - normal_mean)
        print(f"{feature:<30} {all_mean:>12.4f} {normal_mean:>12.4f} {diff:>12.4f}")
    print("-"*80)

else:
    print("\n[4] Skipping normal-only baseline (all windows flagged as anomalies)")

# Compare windows to normal baseline
print("\n[6] Scoring each window's deviation from normal baseline...")
deviations_df = calculator.compare_to_baseline(
    df=features_df,
    baseline_name="2023_all_traffic" if 'predicted_anomaly' not in features_df.columns or features_df['predicted_anomaly'].min() == 0 else "2023_all_traffic",
    std_threshold=3.0
)

print("\nDeviation Statistics:")
print(f"  Mean deviation: {deviations_df['baseline_deviation'].mean():.4f}")
print(f"  Max deviation: {deviations_df['baseline_deviation'].max():.4f}")
print(f"  Min deviation: {deviations_df['baseline_deviation'].min():.4f}")

flagged_by_baseline = (deviations_df['baseline_anomaly_flag'] == 1).sum()
print(f"  Windows > 3σ from mean: {flagged_by_baseline} ({100*flagged_by_baseline/len(deviations_df):.1f}%)")

# Compare baseline flags vs model flags
print("\n[7] Comparing Model Flags vs Baseline Flags...")
agreement = (features_df['predicted_anomaly'] == deviations_df['baseline_anomaly_flag']).sum()
print(f"  Agreement: {agreement}/{len(features_df)} ({100*agreement/len(features_df):.1f}%)")

if (features_df['predicted_anomaly'] == 1).all():
    print("\n⚠️  IMPORTANT: Model flagged ALL 91 windows as anomalous!")
    if flagged_by_baseline < len(features_df):
        print(f"   But baseline flags only {flagged_by_baseline} as >3σ deviation")
        print(f"   → Model may be OVERFITTING to this traffic profile")
        print(f"   → Need labeled attack samples to distinguish true anomalies")

# Save baseline for future use
print("\n[8] Saving baselines...")
calculator.save_baseline("2023_all_traffic", "data/baselines/2023_all_traffic_baseline.json")
if features_df['predicted_anomaly'].min() == 0:
    calculator.save_baseline("2023_normal_only", "data/baselines/2023_normal_only_baseline.json")

# Save deviation scores
deviations_df.to_csv("data/processed/2023_baseline_deviations.csv", index=False)
print(f"✓ Deviation scores saved to data/processed/2023_baseline_deviations.csv")

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
print("\nKey Findings:")
print("• Baseline provides statistical profile of traffic")
print("• Deviation scores show which windows are statistical outliers")
print("• Compare to model scores to assess overfitting")
print("• Next step: Acquire labeled attack data to validate model accuracy")
print("="*80 + "\n")
