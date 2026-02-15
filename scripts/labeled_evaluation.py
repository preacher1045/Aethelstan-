"""
Evaluation metrics for labeled network traffic data.
Supports both labeled normal/anomaly samples and attack classification.
Works independently from main model training pipeline.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from sklearn.metrics import (
    confusion_matrix, 
    classification_report, 
    roc_auc_score, 
    precision_recall_curve,
    f1_score,
    accuracy_score
)


@dataclass
class EvaluationMetrics:
    """Container for model evaluation results."""
    accuracy: float
    precision: float
    recall: float
    f1: float
    confusion_matrix: np.ndarray
    roc_auc: Optional[float] = None
    classification_report: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'accuracy': float(self.accuracy),
            'precision': float(self.precision),
            'recall': float(self.recall),
            'f1': float(self.f1),
            'roc_auc': float(self.roc_auc) if self.roc_auc else None,
            'confusion_matrix': self.confusion_matrix.tolist(),
            'classification_report': self.classification_report
        }


class LabeledDataEvaluator:
    """
    Evaluate anomaly detector against labeled data.
    
    Usage:
        evaluator = LabeledDataEvaluator()
        metrics = evaluator.evaluate(
            predictions=anomaly_scores,
            labels=ground_truth_labels,
            threshold=0.5
        )
    """
    
    def __init__(self):
        self.evaluation_history = []
    
    def evaluate(
        self,
        predictions: np.ndarray,
        labels: np.ndarray,
        threshold: float = 0.5,
        dataset_name: str = "unlabeled"
    ) -> EvaluationMetrics:
        """
        Evaluate model predictions against ground truth labels.
        
        Args:
            predictions: Anomaly scores (0-1) or binary predictions
            labels: Ground truth (0=normal, 1=anomaly)
            threshold: Score threshold for binary classification
            dataset_name: Name of dataset for tracking
        
        Returns:
            EvaluationMetrics with computed metrics
        """
        # Convert scores to binary predictions if needed
        if predictions.max() > 1 or predictions.min() < 0:
            # Normalize if outside [0,1]
            predictions_binary = (predictions > threshold).astype(int)
        else:
            predictions_binary = (predictions > threshold).astype(int)
        
        # Compute metrics
        cm = confusion_matrix(labels, predictions_binary)
        accuracy = accuracy_score(labels, predictions_binary)
        precision = cm[1, 1] / (cm[1, 1] + cm[0, 1]) if (cm[1, 1] + cm[0, 1]) > 0 else 0
        recall = cm[1, 1] / (cm[1, 1] + cm[1, 0]) if (cm[1, 1] + cm[1, 0]) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        # ROC-AUC if predictions are continuous
        try:
            if predictions.max() > 1 or predictions.min() < 0:
                roc_auc = roc_auc_score(labels, predictions)
            else:
                roc_auc = roc_auc_score(labels, predictions) if len(np.unique(labels)) > 1 else None
        except:
            roc_auc = None
        
        # Classification report
        class_report = classification_report(
            labels, 
            predictions_binary,
            target_names=['Normal', 'Anomaly'],
            zero_division=0
        )
        
        metrics = EvaluationMetrics(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1=f1,
            confusion_matrix=cm,
            roc_auc=roc_auc,
            classification_report=class_report
        )
        
        # Store in history
        self.evaluation_history.append({
            'dataset': dataset_name,
            'threshold': threshold,
            'metrics': metrics
        })
        
        return metrics
    
    def evaluate_with_labels_df(
        self,
        df: pd.DataFrame,
        predictions: np.ndarray,
        label_column: str = 'label',
        threshold: float = 0.5,
        dataset_name: str = "unlabeled"
    ) -> Dict:
        """
        Evaluate using DataFrame with label column.
        
        Args:
            df: DataFrame with label column
            predictions: Anomaly scores from model
            label_column: Column name containing labels (0=normal, 1=anomaly)
            threshold: Score threshold for classification
            dataset_name: Dataset identifier
        
        Returns:
            Dictionary with evaluation results and per-attack-type metrics
        """
        labels = df[label_column].values
        metrics = self.evaluate(predictions, labels, threshold, dataset_name)
        
        # Per-attack-type analysis if 'attack_type' column exists
        per_attack = {}
        if 'attack_type' in df.columns:
            for attack in df['attack_type'].unique():
                mask = (df['attack_type'] == attack).values
                if mask.sum() > 0:
                    attack_metrics = self.evaluate(
                        predictions[mask],
                        labels[mask],
                        threshold,
                        f"{dataset_name}_{attack}"
                    )
                    per_attack[attack] = attack_metrics.to_dict()
        
        return {
            'overall': metrics.to_dict(),
            'per_attack': per_attack
        }
    
    def print_metrics(self, metrics: EvaluationMetrics):
        """Pretty-print evaluation metrics."""
        print("\n" + "="*60)
        print("EVALUATION METRICS")
        print("="*60)
        print(f"Accuracy:  {metrics.accuracy:.4f}")
        print(f"Precision: {metrics.precision:.4f}")
        print(f"Recall:    {metrics.recall:.4f}")
        print(f"F1-Score:  {metrics.f1:.4f}")
        if metrics.roc_auc:
            print(f"ROC-AUC:   {metrics.roc_auc:.4f}")
        print("\nConfusion Matrix:")
        print(f"  TN={metrics.confusion_matrix[0,0]}, FP={metrics.confusion_matrix[0,1]}")
        print(f"  FN={metrics.confusion_matrix[1,0]}, TP={metrics.confusion_matrix[1,1]}")
        print("\nClassification Report:")
        print(metrics.classification_report)
        print("="*60 + "\n")
    
    def save_evaluation(self, output_path: str):
        """Save all evaluations to JSON file."""
        output = {
            'evaluations': [
                {
                    'dataset': e['dataset'],
                    'threshold': e['threshold'],
                    'metrics': e['metrics'].to_dict()
                }
                for e in self.evaluation_history
            ]
        }
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"✓ Evaluation results saved to {output_path}")


class DatasetComparator:
    """Compare model performance across multiple datasets."""
    
    def __init__(self):
        self.evaluator = LabeledDataEvaluator()
        self.comparisons = []
    
    def compare_datasets(
        self,
        datasets: Dict[str, Tuple[np.ndarray, np.ndarray]],
        threshold: float = 0.5
    ) -> pd.DataFrame:
        """
        Compare metrics across multiple datasets.
        
        Args:
            datasets: Dict mapping dataset_name -> (predictions, labels)
            threshold: Classification threshold
        
        Returns:
            DataFrame with comparison results
        """
        results = []
        
        for name, (preds, labels) in datasets.items():
            metrics = self.evaluator.evaluate(preds, labels, threshold, name)
            results.append({
                'Dataset': name,
                'Samples': len(labels),
                'Anomalies': labels.sum(),
                'Accuracy': metrics.accuracy,
                'Precision': metrics.precision,
                'Recall': metrics.recall,
                'F1-Score': metrics.f1,
                'ROC-AUC': metrics.roc_auc
            })
        
        df = pd.DataFrame(results)
        self.comparisons.append(df)
        return df
    
    def print_comparison(self, df: pd.DataFrame):
        """Pretty-print dataset comparison."""
        print("\n" + "="*100)
        print("DATASET COMPARISON")
        print("="*100)
        print(df.to_string(index=False))
        print("="*100 + "\n")


if __name__ == "__main__":
    # Example usage
    print("Labeled Evaluation Module - Ready for integration")
    print("\nExample usage:")
    print("""
    from labeled_evaluation import LabeledDataEvaluator
    
    evaluator = LabeledDataEvaluator()
    metrics = evaluator.evaluate(
        predictions=anomaly_scores,  # 0-1 scores
        labels=ground_truth_labels,   # 0=normal, 1=anomaly
        threshold=0.5,
        dataset_name="CTU-13"
    )
    evaluator.print_metrics(metrics)
    """)
