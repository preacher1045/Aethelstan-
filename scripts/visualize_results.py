"""
Visualization of anomaly detection model performance and training data.
"""

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6']

def plot_model_comparison():
    """Compare anomaly detection rates across all three models."""
    
    models = ['Original\n(91 windows)', 'Local Only\n(1,806 windows)', 'Combined\n(1,988 windows)']
    anomaly_rates = [100.0, 4.5, 0.5]
    training_sizes = [91, 1806, 1988]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Plot 1: Anomaly Detection Rates
    bars1 = ax1.bar(models, anomaly_rates, color=colors[:3], alpha=0.8, edgecolor='black')
    ax1.set_ylabel('Anomaly Rate (%)', fontsize=12, fontweight='bold')
    ax1.set_title('Model Performance Comparison\n(Lower is Better)', fontsize=14, fontweight='bold')
    ax1.set_ylim([0, 105])
    ax1.axhline(y=5, color='green', linestyle='--', linewidth=2, label='Target (<5%)')
    ax1.legend()
    
    # Add value labels on bars
    for bar, rate in zip(bars1, anomaly_rates):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{rate:.1f}%', ha='center', va='bottom', fontweight='bold')
    
    # Add improvement annotations
    ax1.annotate('', xy=(1, 4.5), xytext=(0, 100),
                arrowprops=dict(arrowstyle='->', color='green', lw=2))
    ax1.text(0.5, 52, '95.5%\nimprovement', ha='center', fontsize=10, 
             color='green', fontweight='bold', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Plot 2: Training Data Size
    bars2 = ax2.bar(models, training_sizes, color=colors[:3], alpha=0.8, edgecolor='black')
    ax2.set_ylabel('Training Windows', fontsize=12, fontweight='bold')
    ax2.set_title('Training Data Size', fontsize=14, fontweight='bold')
    
    # Add value labels on bars
    for bar, size in zip(bars2, training_sizes):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{size:,}', ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    
    output_path = Path(__file__).parent.parent / "docs" / "model_comparison.png"
    output_path.parent.mkdir(exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    
    return fig

def plot_training_data_distribution():
    """Show distribution of training data across datasets."""
    
    # Data
    datasets = {
        'Local Captures': {
            'Capture_28_01_2026': 201,
            'Capture_29_02_2026-01': 27,
            'capture_31_01_2026': 1195,
            'Capture_31_01_2026_001': 383
        },
        'Enterprise': {
            '2023_test': 91,
            'test_large': 91
        }
    }
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Plot 1: Pie chart of dataset distribution
    total_local = sum(datasets['Local Captures'].values())
    total_enterprise = sum(datasets['Enterprise'].values())
    
    sizes = [total_local, total_enterprise]
    labels = [f'Local Captures\n({total_local} windows)', 
              f'Enterprise\n({total_enterprise} windows)']
    
    wedges, texts, autotexts = ax1.pie(sizes, labels=labels, autopct='%1.1f%%',
                                         colors=[colors[1], colors[3]], startangle=90,
                                         textprops={'fontweight': 'bold', 'fontsize': 11})
    ax1.set_title('Training Data Distribution by Source', fontsize=14, fontweight='bold')
    
    # Plot 2: Bar chart of individual files
    all_files = []
    all_counts = []
    all_colors = []
    
    for file, count in datasets['Local Captures'].items():
        all_files.append(file.replace('_', '\n'))
        all_counts.append(count)
        all_colors.append(colors[1])
    
    for file, count in datasets['Enterprise'].items():
        all_files.append(file.replace('_', '\n'))
        all_counts.append(count)
        all_colors.append(colors[3])
    
    bars = ax2.barh(all_files, all_counts, color=all_colors, alpha=0.8, edgecolor='black')
    ax2.set_xlabel('Number of Windows', fontsize=12, fontweight='bold')
    ax2.set_title('Windows per File', fontsize=14, fontweight='bold')
    ax2.invert_yaxis()
    
    # Add value labels
    for bar, count in zip(bars, all_counts):
        width = bar.get_width()
        ax2.text(width, bar.get_y() + bar.get_height()/2.,
                f' {count}', ha='left', va='center', fontweight='bold')
    
    plt.tight_layout()
    
    output_path = Path(__file__).parent.parent / "docs" / "training_data_distribution.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    
    return fig

def plot_anomaly_score_distribution():
    """Plot distribution of anomaly scores from test predictions."""
    
    # Run prediction on test data
    sys.path.insert(0, str(Path(__file__).parent))
    from data_cleanup import clean_and_engineer_features, select_features
    from backend.ml.inference import AnomalyPredictor
    
    # Load test data
    test_file = Path(__file__).parent.parent / "data" / "processed" / "local_captures" / "Capture_28_01_2026_features.json"
    
    with open(test_file, 'r') as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    df_engineered = clean_and_engineer_features(df)
    df_features = select_features(df_engineered)
    
    # Predict with combined model
    predictor = AnomalyPredictor()
    results = predictor.predict_from_features(df_features)
    
    scores = results['scores']
    predictions = results['predictions']
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Plot 1: Histogram of anomaly scores
    ax1.hist(scores, bins=30, color=colors[2], alpha=0.7, edgecolor='black')
    ax1.axvline(scores.mean(), color='red', linestyle='--', linewidth=2, label=f'Mean: {scores.mean():.3f}')
    ax1.set_xlabel('Anomaly Score', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Frequency', fontsize=12, fontweight='bold')
    ax1.set_title('Distribution of Anomaly Scores\n(Combined Model on Test Data)', 
                  fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Normal vs Anomaly comparison
    normal_scores = scores[predictions == 1]
    anomaly_scores = scores[predictions == -1]
    
    bp = ax2.boxplot([normal_scores, anomaly_scores], 
                      labels=['Normal\n(N={})'.format(len(normal_scores)), 
                             'Anomaly\n(N={})'.format(len(anomaly_scores))],
                      patch_artist=True)
    
    bp['boxes'][0].set_facecolor(colors[2])
    if len(anomaly_scores) > 0:
        bp['boxes'][1].set_facecolor(colors[0])
    
    ax2.set_ylabel('Anomaly Score', fontsize=12, fontweight='bold')
    ax2.set_title('Normal vs Anomalous Windows\n(Lower Score = More Anomalous)', 
                  fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    output_path = Path(__file__).parent.parent / "docs" / "anomaly_score_distribution.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    
    return fig

def plot_improvement_timeline():
    """Show the improvement journey from original to combined model."""
    
    stages = ['Original\nModel', 'Added Local\nCaptures', 'Added Enterprise\nData']
    training_windows = [91, 1806, 1988]
    anomaly_rates = [100.0, 4.5, 0.5]
    
    fig, ax1 = plt.subplots(figsize=(12, 6))
    
    # Plot training windows
    color1 = colors[1]
    ax1.plot(stages, training_windows, marker='o', linewidth=3, markersize=10, 
             color=color1, label='Training Windows')
    ax1.set_xlabel('Model Evolution', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Training Windows', fontsize=12, fontweight='bold', color=color1)
    ax1.tick_params(axis='y', labelcolor=color1)
    
    # Add value labels
    for i, (stage, windows) in enumerate(zip(stages, training_windows)):
        ax1.text(i, windows, f'\n{windows:,}', ha='center', va='bottom', 
                fontweight='bold', color=color1, fontsize=10)
    
    # Plot anomaly rates on secondary axis
    ax2 = ax1.twinx()
    color2 = colors[0]
    ax2.plot(stages, anomaly_rates, marker='s', linewidth=3, markersize=10, 
             color=color2, label='Anomaly Rate (%)', linestyle='--')
    ax2.set_ylabel('Anomaly Rate (%)', fontsize=12, fontweight='bold', color=color2)
    ax2.tick_params(axis='y', labelcolor=color2)
    ax2.set_ylim([0, 105])
    
    # Add value labels
    for i, (stage, rate) in enumerate(zip(stages, anomaly_rates)):
        ax2.text(i, rate, f'{rate:.1f}%\n', ha='center', va='top', 
                fontweight='bold', color=color2, fontsize=10)
    
    # Add target line
    ax2.axhline(y=5, color='green', linestyle=':', linewidth=2, label='Target (<5%)')
    
    # Title and legends
    ax1.set_title('Model Improvement Journey\n(More Training Data = Better Performance)', 
                  fontsize=14, fontweight='bold', pad=20)
    
    # Combine legends
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=10)
    
    ax1.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    output_path = Path(__file__).parent.parent / "docs" / "improvement_timeline.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    
    return fig

def create_all_visualizations():
    """Generate all visualization plots."""
    
    print("\n" + "="*80)
    print("GENERATING VISUALIZATIONS")
    print("="*80 + "\n")
    
    print("1. Model Comparison...")
    plot_model_comparison()
    
    print("\n2. Training Data Distribution...")
    plot_training_data_distribution()
    
    print("\n3. Anomaly Score Distribution...")
    plot_anomaly_score_distribution()
    
    print("\n4. Improvement Timeline...")
    plot_improvement_timeline()
    
    print("\n" + "="*80)
    print("✓ ALL VISUALIZATIONS GENERATED!")
    print("="*80)
    print("\nSaved to: docs/")
    print("  • model_comparison.png")
    print("  • training_data_distribution.png")
    print("  • anomaly_score_distribution.png")
    print("  • improvement_timeline.png")
    print("\n")

if __name__ == "__main__":
    create_all_visualizations()
