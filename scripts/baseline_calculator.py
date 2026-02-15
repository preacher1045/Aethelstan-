"""
Baseline calculator for normal network traffic.
Computes statistical profiles of known-good traffic for comparison.
Operates independently - results can be integrated into main model later.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from scipy import stats


@dataclass
class FeatureBaseline:
    """Statistical baseline for a single feature."""
    name: str
    mean: float
    std: float
    min: float
    max: float
    median: float
    q25: float
    q75: float
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def is_anomalous(self, value: float, std_threshold: float = 3.0) -> bool:
        """Check if value is anomalous (> std_threshold standard deviations away)."""
        if self.std == 0:
            return value != self.mean
        z_score = abs((value - self.mean) / self.std)
        return z_score > std_threshold


@dataclass
class TrafficBaseline:
    """Complete baseline profile for network traffic."""
    name: str
    total_windows: int
    anomaly_count: int
    timestamp: str
    features: Dict[str, Dict]  # Feature name -> baseline stats
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'total_windows': self.total_windows,
            'anomaly_count': self.anomaly_count,
            'timestamp': self.timestamp,
            'features': self.features
        }


class BaselineCalculator:
    """
    Calculate statistical baselines from known-good (normal) traffic.
    
    Usage:
        calculator = BaselineCalculator()
        baseline = calculator.calculate_baseline(
            df=normal_traffic_df,
            baseline_name="office_hours_normal"
        )
    """
    
    def __init__(self):
        self.baselines = {}
        self.feature_stats = {}
    
    def calculate_baseline(
        self,
        df: pd.DataFrame,
        baseline_name: str = "normal_traffic",
        exclude_columns: List[str] = None,
        anomaly_column: Optional[str] = None
    ) -> TrafficBaseline:
        """
        Calculate baseline statistics from DataFrame.
        
        Args:
            df: DataFrame with feature columns
            baseline_name: Name identifier for this baseline
            exclude_columns: Columns to skip (e.g., ['timestamp', 'packet_id'])
            anomaly_column: If provided, filter to only non-anomalous rows
        
        Returns:
            TrafficBaseline with statistical profiles
        """
        # Filter to only normal traffic if label provided
        if anomaly_column and anomaly_column in df.columns:
            normal_df = df[df[anomaly_column] == 0].copy()
            anomaly_count = (df[anomaly_column] == 1).sum()
        else:
            normal_df = df.copy()
            anomaly_count = 0
        
        # Remove non-numeric and excluded columns
        if exclude_columns is None:
            exclude_columns = []
        
        feature_cols = [
            col for col in normal_df.columns
            if col not in exclude_columns
            and pd.api.types.is_numeric_dtype(normal_df[col])
        ]
        
        # Calculate statistics for each feature
        feature_baselines = {}
        for col in feature_cols:
            values = normal_df[col].dropna()
            if len(values) > 0:
                feature_baselines[col] = {
                    'mean': float(values.mean()),
                    'std': float(values.std()),
                    'min': float(values.min()),
                    'max': float(values.max()),
                    'median': float(values.median()),
                    'q25': float(values.quantile(0.25)),
                    'q75': float(values.quantile(0.75)),
                    'count': int(len(values))
                }
        
        baseline = TrafficBaseline(
            name=baseline_name,
            total_windows=len(df),
            anomaly_count=anomaly_count,
            timestamp=pd.Timestamp.now().isoformat(),
            features=feature_baselines
        )
        
        self.baselines[baseline_name] = baseline
        self.feature_stats[baseline_name] = feature_cols
        
        return baseline
    
    def calculate_from_file(
        self,
        features_file: str,
        baseline_name: str = "normal_traffic",
        anomaly_column: Optional[str] = None
    ) -> TrafficBaseline:
        """
        Calculate baseline from JSON feature file.
        
        Args:
            features_file: Path to JSON file with extracted features
            baseline_name: Baseline identifier
            anomaly_column: Column marking anomalies (if labeled)
        
        Returns:
            TrafficBaseline
        """
        # Load JSON (could be array of dicts or object)
        with open(features_file, 'r') as f:
            data = json.load(f)
        
        # Convert to DataFrame
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame([data])
        
        return self.calculate_baseline(
            df=df,
            baseline_name=baseline_name,
            anomaly_column=anomaly_column
        )
    
    def get_baseline(self, name: str) -> Optional[TrafficBaseline]:
        """Retrieve stored baseline by name."""
        return self.baselines.get(name)
    
    def compare_to_baseline(
        self,
        df: pd.DataFrame,
        baseline_name: str,
        std_threshold: float = 3.0
    ) -> pd.DataFrame:
        """
        Compare data to baseline, flagging deviations.
        
        Args:
            df: Data to evaluate
            baseline_name: Which baseline to use
            std_threshold: How many stds away = anomalous
        
        Returns:
            DataFrame with deviation scores and anomaly flags
        """
        baseline = self.get_baseline(baseline_name)
        if not baseline:
            raise ValueError(f"Baseline '{baseline_name}' not found")
        
        result_df = df.copy()
        feature_cols = self.feature_stats.get(baseline_name, [])
        
        # Calculate z-scores for each feature
        deviation_scores = []
        for idx, row in df.iterrows():
            row_deviations = []
            for col in feature_cols:
                if col in baseline.features:
                    stats_dict = baseline.features[col]
                    mean = stats_dict['mean']
                    std = stats_dict['std']
                    
                    if std > 0:
                        z_score = abs((row[col] - mean) / std)
                    else:
                        z_score = 0 if row[col] == mean else 1
                    
                    row_deviations.append(z_score)
            
            # Max deviation for this window
            max_deviation = max(row_deviations) if row_deviations else 0
            deviation_scores.append(max_deviation)
        
        result_df['baseline_deviation'] = deviation_scores
        result_df['baseline_anomaly_flag'] = (
            np.array(deviation_scores) > std_threshold
        ).astype(int)
        
        return result_df
    
    def print_baseline(self, baseline_name: str):
        """Pretty-print baseline statistics."""
        baseline = self.get_baseline(baseline_name)
        if not baseline:
            print(f"Baseline '{baseline_name}' not found")
            return
        
        print("\n" + "="*80)
        print(f"BASELINE: {baseline.name}")
        print("="*80)
        print(f"Windows: {baseline.total_windows} | Anomalies in source: {baseline.anomaly_count}")
        print(f"Timestamp: {baseline.timestamp}")
        print("\nFeature Statistics:")
        print("-"*80)
        
        # Create summary table
        stats_data = []
        for feature, stats_dict in sorted(baseline.features.items()):
            stats_data.append({
                'Feature': feature,
                'Mean': f"{stats_dict['mean']:.4f}",
                'Std': f"{stats_dict['std']:.4f}",
                'Min': f"{stats_dict['min']:.4f}",
                'Max': f"{stats_dict['max']:.4f}",
                'Median': f"{stats_dict['median']:.4f}"
            })
        
        df_stats = pd.DataFrame(stats_data)
        print(df_stats.to_string(index=False))
        print("="*80 + "\n")
    
    def save_baseline(self, baseline_name: str, output_path: str):
        """Save baseline to JSON file."""
        baseline = self.get_baseline(baseline_name)
        if not baseline:
            raise ValueError(f"Baseline '{baseline_name}' not found")
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(baseline.to_dict(), f, indent=2)
        print(f"✓ Baseline '{baseline_name}' saved to {output_path}")
    
    def load_baseline(self, baseline_path: str) -> TrafficBaseline:
        """Load baseline from JSON file."""
        with open(baseline_path, 'r') as f:
            data = json.load(f)
        
        baseline = TrafficBaseline(
            name=data['name'],
            total_windows=data['total_windows'],
            anomaly_count=data['anomaly_count'],
            timestamp=data['timestamp'],
            features=data['features']
        )
        
        self.baselines[baseline.name] = baseline
        # Infer feature columns from baseline
        self.feature_stats[baseline.name] = list(baseline.features.keys())
        
        return baseline
    
    def compare_baselines(self, baseline_names: List[str]) -> pd.DataFrame:
        """
        Compare statistics across multiple baselines.
        
        Args:
            baseline_names: List of baseline names to compare
        
        Returns:
            DataFrame showing key statistics for each baseline
        """
        comparison = []
        for name in baseline_names:
            baseline = self.get_baseline(name)
            if baseline:
                # Get aggregate stats
                feature_means = [
                    stats['mean'] for stats in baseline.features.values()
                ]
                feature_stds = [
                    stats['std'] for stats in baseline.features.values()
                ]
                
                comparison.append({
                    'Baseline': name,
                    'Windows': baseline.total_windows,
                    'Features': len(baseline.features),
                    'Avg Feature Mean': np.mean(feature_means),
                    'Avg Feature Std': np.mean(feature_stds)
                })
        
        return pd.DataFrame(comparison)


class BaselineManager:
    """Manage multiple baselines for different scenarios."""
    
    def __init__(self):
        self.baselines = {}
        self.calculator = BaselineCalculator()
    
    def create_scenario(
        self,
        scenario_name: str,
        data_dict: Dict[str, pd.DataFrame]
    ):
        """
        Create baselines for different network scenarios.
        
        Args:
            scenario_name: Name for this scenario set
            data_dict: Dict mapping baseline_name -> DataFrame
        """
        self.baselines[scenario_name] = {}
        for name, df in data_dict.items():
            baseline = self.calculator.calculate_baseline(df, baseline_name=name)
            self.baselines[scenario_name][name] = baseline
    
    def save_scenario(self, scenario_name: str, output_dir: str):
        """Save all baselines in a scenario."""
        scenario = self.baselines.get(scenario_name)
        if not scenario:
            raise ValueError(f"Scenario '{scenario_name}' not found")
        
        scenario_path = Path(output_dir) / scenario_name
        scenario_path.mkdir(parents=True, exist_ok=True)
        
        for baseline_name, baseline in scenario.items():
            file_path = scenario_path / f"{baseline_name}_baseline.json"
            with open(file_path, 'w') as f:
                json.dump(baseline.to_dict(), f, indent=2)
        
        print(f"✓ Scenario '{scenario_name}' saved to {scenario_path}")


if __name__ == "__main__":
    print("Baseline Calculator Module - Ready for integration")
    print("\nExample usage:")
    print("""
    from baseline_calculator import BaselineCalculator
    
    calculator = BaselineCalculator()
    
    # From DataFrame
    baseline = calculator.calculate_baseline(
        df=normal_traffic_df,
        baseline_name="office_hours"
    )
    
    # From JSON file
    baseline = calculator.calculate_from_file(
        features_file="data/normal_traffic_features.json",
        baseline_name="datacenter_normal"
    )
    
    # Compare new data to baseline
    deviations = calculator.compare_to_baseline(
        df=new_data_df,
        baseline_name="office_hours"
    )
    
    # Save for later use
    calculator.save_baseline("office_hours", "baselines/office_hours.json")
    """)
