"""
Test production model on new data, generate insights, and create visualizations.
"""

import sys
import json
import subprocess
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.ml.production_inference import predict_with_feature_engineering
from backend.insight.generator import InsightGenerator

def extract_features_from_pcap(pcap_path, output_json=None):
    """Extract features from PCAP file using Rust extractor."""
    
    pcap_path = Path(pcap_path)
    if not pcap_path.exists():
        raise FileNotFoundError(f"PCAP file not found: {pcap_path}")
    
    if output_json is None:
        output_json = Path(__file__).parent.parent / "data" / "processed" / f"{pcap_path.stem}_features.json"
    
    output_json = Path(output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    
    # Rust extractor path
    extractor_path = Path(__file__).parent.parent / "backend" / "features" / "rust_extractor" / "target" / "release" / "rust_extractor.exe"
    
    if not extractor_path.exists():
        raise FileNotFoundError(f"Rust extractor not found: {extractor_path}")
    
    print(f"\n{'='*80}")
    print(f"EXTRACTING FEATURES FROM: {pcap_path.name}")
    print(f"{'='*80}")
    
    cmd = [str(extractor_path), str(pcap_path), str(output_json)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error running extractor: {result.stderr}")
        raise RuntimeError(f"Feature extraction failed for {pcap_path}")
    
    print(result.stdout)
    return str(output_json)

def test_model_and_generate_insights(pcap_path):
    """Test model on new PCAP and generate insights."""
    
    pcap_path = Path(pcap_path)
    
    # Step 1: Extract features
    print(f"\n{'='*80}")
    print("STEP 1: FEATURE EXTRACTION")
    print(f"{'='*80}")
    
    features_json = extract_features_from_pcap(pcap_path)
    print(f"✓ Features extracted: {features_json}")
    
    # Step 2: Run model inference
    print(f"\n{'='*80}")
    print("STEP 2: MODEL INFERENCE")
    print(f"{'='*80}")
    
    results = predict_with_feature_engineering(features_json)
    
    print(f"\nInference Results:")
    print(f"  • Windows analyzed: {results['n_samples']}")
    print(f"  • Anomalies detected: {results['anomaly_count']} ({results['anomaly_percentage']:.1f}%)")
    print(f"  • Avg score: {results['scores'].mean():.3f}")
    
    # Step 3: Generate insights
    print(f"\n{'='*80}")
    print("STEP 3: INSIGHT GENERATION")
    print(f"{'='*80}")
    
    generator = InsightGenerator(max_alerts=5)
    records = results['detailed_results'].to_dict('records')
    insights = generator.generate(records)
    
    print(f"\nInsights:")
    print(f"  • Summary: {insights['summary']}")
    print(f"  • Total alerts: {len(insights['alerts'])}")
    
    if insights['alerts']:
        print(f"\n  Top Alerts:")
        for i, alert in enumerate(insights['alerts'][:3], 1):
            print(f"    {i}. [{alert['severity']}] {alert['summary']} (confidence: {alert['confidence']:.2f})")
    
    # Save raw results
    output_dir = Path(__file__).parent.parent / "docs" / "model_insight"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save insights
    insights_file = output_dir / f"{pcap_path.stem}_insights.json"
    with open(insights_file, 'w') as f:
        json.dump(insights, f, indent=2)
    print(f"\n✓ Insights saved: {insights_file}")
    
    # Save predictions
    predictions_file = output_dir / f"{pcap_path.stem}_predictions.json"
    predictions_data = results['detailed_results'].to_dict('records')
    with open(predictions_file, 'w') as f:
        json.dump(predictions_data, f, indent=2)
    print(f"✓ Predictions saved: {predictions_file}")
    
    return results, insights

def visualize_results(results, insights, pcap_name, output_dir="docs/model_insight"):
    """Create comprehensive visualizations."""
    
    output_dir = Path(__file__).parent.parent / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*80}")
    print("STEP 4: VISUALIZATION")
    print(f"{'='*80}")
    
    # Plot 1: Anomaly Score Distribution
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f'Model Insights - {pcap_name}', fontsize=16, fontweight='bold')
    
    df = results['detailed_results']
    scores = results['scores']
    predictions = results['predictions']
    
    # Subplot 1: Score distribution
    axes[0, 0].hist(scores, bins=30, color='#3498db', alpha=0.7, edgecolor='black')
    axes[0, 0].axvline(scores.mean(), color='red', linestyle='--', linewidth=2, label=f'Mean: {scores.mean():.3f}')
    axes[0, 0].set_xlabel('Anomaly Score')
    axes[0, 0].set_ylabel('Frequency')
    axes[0, 0].set_title('Distribution of Anomaly Scores')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # Subplot 2: Normal vs Anomaly
    normal_scores = scores[predictions == 1]
    anomaly_scores = scores[predictions == -1]
    
    bp = axes[0, 1].boxplot([normal_scores, anomaly_scores],
                             labels=[f'Normal\n(N={len(normal_scores)})', 
                                    f'Anomaly\n(N={len(anomaly_scores)})'],
                             patch_artist=True)
    bp['boxes'][0].set_facecolor('#2ecc71')
    if len(anomaly_scores) > 0:
        bp['boxes'][1].set_facecolor('#e74c3c')
    
    axes[0, 1].set_ylabel('Anomaly Score')
    axes[0, 1].set_title('Normal vs Anomalous Windows')
    axes[0, 1].grid(True, alpha=0.3, axis='y')
    
    # Subplot 3: Packet count vs Anomaly Score
    axes[1, 0].scatter(df['packet_count'], scores, 
                      c=predictions, cmap='RdYlGn_r', alpha=0.6, s=50)
    axes[1, 0].set_xlabel('Packet Count')
    axes[1, 0].set_ylabel('Anomaly Score')
    axes[1, 0].set_title('Packet Count vs Anomaly Score')
    axes[1, 0].grid(True, alpha=0.3)
    
    # Subplot 4: Timeline of anomalies
    window_indices = range(len(scores))
    colors = ['#e74c3c' if pred == -1 else '#2ecc71' for pred in predictions]
    axes[1, 1].scatter(window_indices, scores, c=colors, alpha=0.6, s=30)
    axes[1, 1].set_xlabel('Window Index')
    axes[1, 1].set_ylabel('Anomaly Score')
    axes[1, 1].set_title('Anomaly Timeline')
    axes[1, 1].axhline(y=scores.mean(), color='orange', linestyle='--', linewidth=1, label='Mean')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    viz_file = output_dir / f"{Path(pcap_name).stem}_visualization.png"
    plt.savefig(viz_file, dpi=300, bbox_inches='tight')
    print(f"✓ Visualization saved: {viz_file}")
    
    # Plot 2: Summary Statistics
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle(f'Summary Statistics - {pcap_name}', fontsize=14, fontweight='bold')
    
    # Summary stats
    stats = insights['stats']
    
    # Pie chart: Anomaly vs Normal
    sizes = [stats['total_windows'] - stats['anomalies'], stats['anomalies']]
    labels = [f"Normal\n({sizes[0]})", f"Anomaly\n({sizes[1]})"]
    colors = ['#2ecc71', '#e74c3c']
    
    axes[0].pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
               startangle=90, explode=(0, 0.1) if sizes[1] > 0 else (0, 0))
    axes[0].set_title('Window Classification')
    
    # Key metrics
    metrics_text = f"""
    Total Windows: {stats['total_windows']}
    Anomalies: {stats['anomalies']}
    Anomaly Rate: {(stats['anomalies']/stats['total_windows']*100):.1f}%
    
    Score Stats:
    Mean: {scores.mean():.3f}
    Std: {scores.std():.3f}
    Min: {scores.min():.3f}
    Max: {scores.max():.3f}
    
    Alerts Generated: {len(insights['alerts'])}
    """
    
    axes[1].text(0.1, 0.5, metrics_text, fontsize=11, family='monospace',
                verticalalignment='center', bbox=dict(boxstyle='round', 
                facecolor='wheat', alpha=0.5))
    axes[1].axis('off')
    
    plt.tight_layout()
    
    summary_file = output_dir / f"{Path(pcap_name).stem}_summary.png"
    plt.savefig(summary_file, dpi=300, bbox_inches='tight')
    print(f"✓ Summary saved: {summary_file}")
    
    plt.close('all')

def main():
    """Main test workflow."""
    
    # Check for 2.pcap
    base_dir = Path(__file__).parent.parent
    pcap_path = base_dir / "data" / "raw" / "2.pcap"
    
    if not pcap_path.exists():
        print(f"\n❌ ERROR: {pcap_path} not found!")
        print(f"\nPlace 2.pcap in the data/raw/ directory and try again.")
        sys.exit(1)
    
    print(f"\n{'='*80}")
    print(f"NEW MODEL TEST & INSIGHT GENERATION")
    print(f"{'='*80}")
    print(f"Testing: {pcap_path}")
    
    # Run full pipeline
    results, insights = test_model_and_generate_insights(pcap_path)
    
    # Generate visualizations
    visualize_results(results, insights, pcap_path.name)
    
    # Print summary
    print(f"\n{'='*80}")
    print("COMPLETE!")
    print(f"{'='*80}")
    print(f"\nResults saved to: docs/model_insight/")
    print(f"  • {pcap_path.stem}_insights.json")
    print(f"  • {pcap_path.stem}_predictions.json")
    print(f"  • {pcap_path.stem}_visualization.png")
    print(f"  • {pcap_path.stem}_summary.png")
    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    main()
