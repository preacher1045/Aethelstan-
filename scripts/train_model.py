"""
Complete training pipeline for network anomaly detection model.

Workflow:
1. Load rust feature extractor output (window_features.json)
2. Clean and preprocess data (scripts/data_cleanup.py)
3. Train model (backend/ml/model.py)
4. Evaluate on validation set
5. Save trained model for inference
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
import logging
import json
import pickle

# Change to project root
os.chdir(Path(__file__).parent.parent)
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the cleanup and model code directly
from data_cleanup import load_rust_output, clean_and_engineer_features, select_features, remove_outliers

# Import model components manually to avoid path issues
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split


class SimpleAnomalyDetector:
    """Simple Isolation Forest wrapper for anomaly detection."""
    
    def __init__(self, n_estimators=100, contamination=0.1, random_state=42):
        self.model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=random_state
        )
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.feature_names = None
    
    def fit(self, X):
        if isinstance(X, pd.DataFrame):
            self.feature_names = X.columns.tolist()
            X = X.values
        
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self.is_fitted = True
        logger.info(f"Model fitted on {X.shape[0]} samples with {X.shape[1]} features")
    
    def predict(self, X):
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted first")
        
        if isinstance(X, pd.DataFrame):
            X = X.values
        
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)
    
    def decision_function(self, X):
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted first")
        
        if isinstance(X, pd.DataFrame):
            X = X.values
        
        X_scaled = self.scaler.transform(X)
        return self.model.decision_function(X_scaled)
    
    def save(self, filepath):
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        state = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names
        }
        with open(filepath, 'wb') as f:
            pickle.dump(state, f)
        logger.info(f"Model saved to {filepath}")


def train_anomaly_model(
    features_json="data/processed/window_features.json",
    output_model="models/network_anomaly_model.pkl",
    remove_outliers_flag=False,
    test_size=0.2,
    random_state=42
):
    """
    Train anomaly detection model end-to-end.
    """
    
    logger.info("=" * 60)
    logger.info("NETWORK ANOMALY DETECTION - TRAINING PIPELINE")
    logger.info("=" * 60)
    
    # Step 1: Load and clean data
    logger.info("\n📊 Step 1: Loading and cleaning data...")
    df = load_rust_output(features_json)
    df = clean_and_engineer_features(df)
    
    if remove_outliers_flag:
        df = remove_outliers(df)
    
    df = select_features(df)
    
    logger.info(f"Data shape: {df.shape}")
    logger.info(f"Features: {list(df.columns)}")
    
    # Step 2: Split data
    logger.info("\n📊 Step 2: Splitting into train/validation...")
    X_train, X_val = train_test_split(df, test_size=test_size, random_state=random_state)
    logger.info(f"Training samples: {len(X_train)}")
    logger.info(f"Validation samples: {len(X_val)}")
    
    # Step 3: Train model
    logger.info("\n🤖 Step 3: Training model...")
    detector = SimpleAnomalyDetector(random_state=random_state)
    detector.fit(X_train)
    
    # Step 4: Evaluate
    logger.info("\n📈 Step 4: Evaluating...")
    
    train_preds = detector.predict(X_train)
    train_scores = detector.decision_function(X_train)
    train_anomalies = (train_preds == -1).sum()
    
    val_preds = detector.predict(X_val)
    val_scores = detector.decision_function(X_val)
    val_anomalies = (val_preds == -1).sum()
    
    logger.info("\nTraining Set:")
    logger.info(f"  Anomalies: {train_anomalies} / {len(X_train)} ({100*train_anomalies/len(X_train):.2f}%)")
    logger.info(f"  Scores - Mean: {train_scores.mean():.4f}, Std: {train_scores.std():.4f}")
    
    logger.info("\nValidation Set:")
    logger.info(f"  Anomalies: {val_anomalies} / {len(X_val)} ({100*val_anomalies/len(X_val):.2f}%)")
    logger.info(f"  Scores - Mean: {val_scores.mean():.4f}, Std: {val_scores.std():.4f}")
    
    # Step 5: Save model
    logger.info("\n💾 Step 5: Saving model...")
    detector.save(output_model)
    
    logger.info("=" * 60)
    logger.info("✅ TRAINING COMPLETE")
    logger.info("=" * 60)
    
    return detector


def quick_train():
    """Quick training with default parameters."""
    detector = train_anomaly_model(
        features_json="data/processed/window_features.json",
        output_model="models/network_anomaly_model.pkl",
        remove_outliers_flag=False,
        test_size=0.2,
        random_state=42
    )
    return detector


if __name__ == "__main__":
    quick_train()
