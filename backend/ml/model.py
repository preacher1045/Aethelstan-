import numpy as np
import pandas as pd
import pickle
import json
from pathlib import Path
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Isolation Forest-based anomaly detector for network traffic analysis."""
    
    def __init__(self, n_estimators=100, contamination=0.1, random_state=42):
        self.model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=random_state
        )
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.feature_names = None

    def fit(self, X, normalize=True):
        """
        Fit the Isolation Forest model to training data.
        
        Parameters:
            X (array-like): Training data shape (n_samples, n_features)
            normalize (bool): Whether to normalize features before fitting
        """
        if isinstance(X, pd.DataFrame):
            self.feature_names = X.columns.tolist()
            X = X.values
        
        if normalize:
            X = self.scaler.fit_transform(X)
        
        self.model.fit(X)
        self.is_fitted = True
        logger.info(f"Model fitted on {X.shape[0]} samples with {X.shape[1]} features")

    def predict(self, X, normalize=True):
        """
        Predict anomalies (-1 for anomaly, 1 for normal).
        
        Parameters:
            X (array-like): Data to predict
            normalize (bool): Whether to normalize features
            
        Returns:
            array: Predictions (-1 or 1)
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before prediction.")
        
        if isinstance(X, pd.DataFrame):
            X = X.values
        
        if normalize:
            X = self.scaler.transform(X)
        
        return self.model.predict(X)

    def decision_function(self, X, normalize=True):
        """
        Compute anomaly scores (lower = more anomalous).
        
        Parameters:
            X (array-like): Data to score
            normalize (bool): Whether to normalize features
            
        Returns:
            array: Anomaly scores
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before computing scores.")
        
        if isinstance(X, pd.DataFrame):
            X = X.values
        
        if normalize:
            X = self.scaler.transform(X)
        
        return self.model.decision_function(X)

    def save(self, filepath):
        """Save model and scaler to disk."""
        if not self.is_fitted:
            raise RuntimeError("Cannot save unfitted model.")
        
        state = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(state, f)
        
        logger.info(f"Model saved to {filepath}")

    def load(self, filepath):
        """Load model and scaler from disk."""
        with open(filepath, 'rb') as f:
            state = pickle.load(f)
        
        self.model = state['model']
        self.scaler = state['scaler']
        self.feature_names = state['feature_names']
        self.is_fitted = True
        
        logger.info(f"Model loaded from {filepath}")


class NetworkAnomalyModel:
    """End-to-end model for network anomaly detection with training pipeline."""
    
    def __init__(self, model_type='isolation_forest', random_state=42):
        """
        Initialize model.
        
        Parameters:
            model_type (str): 'isolation_forest' or 'random_forest'
            random_state (int): Random seed for reproducibility
        """
        self.model_type = model_type
        self.random_state = random_state
        self.detector = None
        self.scaler = StandardScaler()
        self.feature_names = None
        self.X_train = None
        self.X_val = None
        
    def _create_model(self):
        """Create the appropriate model instance."""
        if self.model_type == 'isolation_forest':
            self.detector = AnomalyDetector(random_state=self.random_state)
        else:
            raise ValueError(f"Unknown model_type: {self.model_type}")
    
    def train(self, X_train, X_val=None, normalize=True, test_size=0.2):
        """
        Train the model on provided data.
        
        Parameters:
            X_train (DataFrame or array): Training data
            X_val (DataFrame or array, optional): Validation data
            normalize (bool): Whether to normalize features
            test_size (float): If X_val is None, split train data by this ratio
        """
        self._create_model()
        
        # Store feature names
        if isinstance(X_train, pd.DataFrame):
            self.feature_names = X_train.columns.tolist()
        
        # Split if validation set not provided
        if X_val is None:
            X_train, X_val = train_test_split(
                X_train, 
                test_size=test_size, 
                random_state=self.random_state
            )
        
        self.X_train = X_train
        self.X_val = X_val
        
        # Fit scaler on training data
        if normalize:
            if isinstance(X_train, pd.DataFrame):
                X_train_scaled = self.scaler.fit_transform(X_train)
            else:
                X_train_scaled = self.scaler.fit_transform(X_train)
        else:
            X_train_scaled = X_train
        
        # Train detector
        self.detector.fit(X_train_scaled, normalize=False)
        logger.info(f"Training complete. Model type: {self.model_type}")
    
    def evaluate(self, X_data):
        """
        Evaluate model performance on data.
        
        Parameters:
            X_data (DataFrame or array): Data to evaluate
            
        Returns:
            dict: Evaluation metrics
        """
        if self.detector is None:
            raise RuntimeError("Model not trained yet.")
        
        predictions = self.predict(X_data)
        scores = self.decision_function(X_data)
        
        # Count anomalies
        n_anomalies = (predictions == -1).sum()
        anomaly_ratio = n_anomalies / len(predictions)
        
        metrics = {
            'n_samples': len(predictions),
            'n_anomalies': n_anomalies,
            'anomaly_ratio': anomaly_ratio,
            'mean_score': scores.mean(),
            'std_score': scores.std(),
            'min_score': scores.min(),
            'max_score': scores.max()
        }
        
        logger.info(f"Evaluation: {metrics}")
        return metrics
    
    def predict(self, X):
        """Predict anomalies on new data."""
        if self.detector is None:
            raise RuntimeError("Model not trained yet.")
        return self.detector.predict(X, normalize=True)
    
    def decision_function(self, X):
        """Get anomaly scores for new data."""
        if self.detector is None:
            raise RuntimeError("Model not trained yet.")
        return self.detector.decision_function(X, normalize=True)
    
    def save(self, filepath):
        """Save trained model to disk."""
        if self.detector is None:
            raise RuntimeError("No model to save.")
        
        state = {
            'model_type': self.model_type,
            'detector': self.detector,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'random_state': self.random_state
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'wb') as f:
            pickle.dump(state, f)
        
        logger.info(f"Model saved to {filepath}")
    
    def load(self, filepath):
        """Load trained model from disk."""
        with open(filepath, 'rb') as f:
            state = pickle.load(f)
        
        self.model_type = state['model_type']
        self.detector = state['detector']
        self.scaler = state['scaler']
        self.feature_names = state['feature_names']
        self.random_state = state['random_state']
        
        logger.info(f"Model loaded from {filepath}")
