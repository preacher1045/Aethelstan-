"""
Inference module for making predictions with trained network anomaly models.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
import pickle
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default production model path
DEFAULT_MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "network_anomaly_model_combined.pkl"


class AnomalyPredictor:
    """Load and use trained anomaly detection models for inference."""
    
    def __init__(self, model_path=None):
        """
        Initialize predictor with trained model.
        
        Parameters:
            model_path (str): Path to saved model file (.pkl)
                            If None, uses DEFAULT_MODEL_PATH (production model)
        """
        if model_path is None:
            model_path = DEFAULT_MODEL_PATH
            logger.info(f"Using default production model: {model_path}")
        
        with open(model_path, 'rb') as f:
            state = pickle.load(f)
        
        # Support both old format (dict) and new format (AnomalyDetector object)
        if isinstance(state, dict):
            # Old format: {'model': ..., 'scaler': ..., 'feature_names': ...}
            self.model = state['model']
            self.scaler = state['scaler']
            self.feature_names = state.get('feature_names', None)
            self._is_new_format = False
            logger.info(f"Loaded old format model from {model_path}")
        else:
            # New format: AnomalyDetector object with built-in methods
            self.model_obj = state
            self.model = None
            self.scaler = None
            self.feature_names = None
            self._is_new_format = True
            logger.info(f"Loaded new format model (AnomalyDetector) from {model_path}")
        
        logger.info(f"Predictor initialized with model from {model_path}")
    
    def predict_from_features(self, features_df):
        """
        Predict anomalies from network features.
        
        Parameters:
            features_df (DataFrame): Network features (must have same columns as training)
            
        Returns:
            dict: Predictions and scores
        """
        if self._is_new_format:
            # New format: AnomalyDetector object handles everything
            predictions = self.model_obj.predict(features_df)
            scores = self.model_obj.predict_anomaly_score(features_df)
        else:
            # Old format: Manual scaling and prediction
            # Ensure features match training features
            if self.feature_names:
                missing_features = set(self.feature_names) - set(features_df.columns)
                if missing_features:
                    raise ValueError(f"Missing features: {missing_features}")
                
                features_df = features_df[self.feature_names]
            
            # Scale and predict
            if isinstance(features_df, pd.DataFrame):
                X = features_df.values
            else:
                X = features_df
            
            X_scaled = self.scaler.transform(X)
            predictions = self.model.predict(X_scaled)
            scores = self.model.decision_function(X_scaled)
        
        return {
            'predictions': predictions,
            'scores': scores,
            'anomaly_count': (predictions == -1).sum(),
            'anomaly_ratio': (predictions == -1).mean()
        }
    
    def predict_from_json(self, json_path):
        """
        Load features from JSON and predict.
        
        Parameters:
            json_path (str): Path to JSON features file
            
        Returns:
            dict: Predictions with metadata
        """
        with open(json_path, 'r') as f:
            features = json.load(f)
        
        df = pd.DataFrame(features)
        logger.info(f"Loaded {len(df)} samples from {json_path}")
        
        results = self.predict_from_features(df)
        results['n_samples'] = len(df)
        results['features_file'] = str(json_path)
        
        return results
    
    def predict_and_label(self, features_df):
        """
        Predict anomalies and add labels to dataframe.
        
        Parameters:
            features_df (DataFrame): Network features
            
        Returns:
            DataFrame: Original features with 'anomaly' and 'score' columns
        """
        if self.feature_names:
            features_df = features_df[self.feature_names]
        
        if isinstance(features_df, pd.DataFrame):
            X = features_df.values
        else:
            X = features_df
        
        X_scaled = self.scaler.transform(X)
        predictions = self.model.predict(X_scaled)
        scores = self.model.decision_function(X_scaled)
        
        result_df = features_df.copy() if isinstance(features_df, pd.DataFrame) else pd.DataFrame(features_df)
        result_df['anomaly'] = predictions
        result_df['score'] = scores
        result_df['is_anomaly'] = result_df['anomaly'] == -1
        
        return result_df
    
    def get_top_anomalies(self, features_df, top_n=10):
        """
        Get the top N most anomalous samples.
        
        Parameters:
            features_df (DataFrame): Network features
            top_n (int): Number of top anomalies to return
            
        Returns:
            DataFrame: Top anomalies sorted by score
        """
        result_df = self.predict_and_label(features_df)
        # Lower score = more anomalous
        top_anomalies = result_df.nsmallest(top_n, 'score')
        
        return top_anomalies
    
    def get_summary_report(self, features_df):
        """
        Generate a summary report of predictions.
        
        Parameters:
            features_df (DataFrame): Network features
            
        Returns:
            dict: Summary statistics
        """
        result_df = self.predict_and_label(features_df)
        
        report = {
            'total_samples': len(result_df),
            'normal_samples': (result_df['anomaly'] == 1).sum(),
            'anomalous_samples': (result_df['anomaly'] == -1).sum(),
            'anomaly_percentage': (result_df['anomaly'] == -1).mean() * 100,
            'mean_score': result_df['score'].mean(),
            'min_score': result_df['score'].min(),
            'max_score': result_df['score'].max(),
            'std_score': result_df['score'].std()
        }
        
        logger.info(f"Summary: {report['anomalous_samples']} anomalies detected "
                    f"({report['anomaly_percentage']:.2f}%)")
        
        return report


def predict_batch(model_path, features_json_path, output_path=None):
    """
    Utility function to run batch predictions.
    
    Parameters:
        model_path (str): Path to trained model
        features_json_path (str): Path to features JSON file
        output_path (str, optional): Path to save results as JSON
    """
    predictor = AnomalyPredictor(model_path)
    results = predictor.predict_from_json(features_json_path)
    
    logger.info(f"Anomalies detected: {results['anomaly_count']} / {results['n_samples']}")
    
    if output_path:
        # Load full data with predictions
        with open(features_json_path, 'r') as f:
            features = json.load(f)
        
        df = pd.DataFrame(features)
        result_df = predictor.predict_and_label(df)
        
        # Convert to JSON-serializable format
        output_data = result_df.to_dict(orient='records')
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        logger.info(f"Results saved to {output_path}")
    
    return results

    
    def predict_from_features(self, features_df):
        """
        Predict anomalies from network features.
        
        Parameters:
            features_df (DataFrame): Network features (must have same columns as training)
            
        Returns:
            dict: Predictions and scores
        """
        # Ensure features match training features
        if self.model.feature_names:
            missing_features = set(self.model.feature_names) - set(features_df.columns)
            if missing_features:
                raise ValueError(f"Missing features: {missing_features}")
            
            features_df = features_df[self.model.feature_names]
        
        # Get predictions and scores
        predictions = self.model.predict(features_df)
        scores = self.model.decision_function(features_df)
        
        return {
            'predictions': predictions,
            'scores': scores,
            'anomaly_count': (predictions == -1).sum(),
            'anomaly_ratio': (predictions == -1).mean()
        }
    
    def predict_from_json(self, json_path):
        """
        Load features from JSON and predict.
        
        Parameters:
            json_path (str): Path to JSON features file
            
        Returns:
            dict: Predictions with metadata
        """
        with open(json_path, 'r') as f:
            features = json.load(f)
        
        df = pd.DataFrame(features)
        logger.info(f"Loaded {len(df)} samples from {json_path}")
        
        results = self.predict_from_features(df)
        results['n_samples'] = len(df)
        results['features_file'] = str(json_path)
        
        return results
    
    def predict_and_label(self, features_df):
        """
        Predict anomalies and add labels to dataframe.
        
        Parameters:
            features_df (DataFrame): Network features
            
        Returns:
            DataFrame: Original features with 'anomaly' and 'score' columns
        """
        predictions = self.model.predict(features_df)
        scores = self.model.decision_function(features_df)
        
        result_df = features_df.copy()
        result_df['anomaly'] = predictions
        result_df['score'] = scores
        result_df['is_anomaly'] = result_df['anomaly'] == -1
        
        return result_df
    
    def get_top_anomalies(self, features_df, top_n=10):
        """
        Get the top N most anomalous samples.
        
        Parameters:
            features_df (DataFrame): Network features
            top_n (int): Number of top anomalies to return
            
        Returns:
            DataFrame: Top anomalies sorted by score
        """
        result_df = self.predict_and_label(features_df)
        # Lower score = more anomalous
        top_anomalies = result_df.nsmallest(top_n, 'score')
        
        return top_anomalies
    
    def get_summary_report(self, features_df):
        """
        Generate a summary report of predictions.
        
        Parameters:
            features_df (DataFrame): Network features
            
        Returns:
            dict: Summary statistics
        """
        result_df = self.predict_and_label(features_df)
        
        report = {
            'total_samples': len(result_df),
            'normal_samples': (result_df['anomaly'] == 1).sum(),
            'anomalous_samples': (result_df['anomaly'] == -1).sum(),
            'anomaly_percentage': (result_df['anomaly'] == -1).mean() * 100,
            'mean_score': result_df['score'].mean(),
            'min_score': result_df['score'].min(),
            'max_score': result_df['score'].max(),
            'std_score': result_df['score'].std()
        }
        
        logger.info(f"Summary: {report['anomalous_samples']} anomalies detected "
                    f"({report['anomaly_percentage']:.2f}%)")
        
        return report


def predict_batch(model_path, features_json_path, output_path=None):
    """
    Utility function to run batch predictions.
    
    Parameters:
        model_path (str): Path to trained model
        features_json_path (str): Path to features JSON file
        output_path (str, optional): Path to save results as JSON
    """
    predictor = AnomalyPredictor(model_path)
    results = predictor.predict_from_json(features_json_path)
    
    logger.info(f"Anomalies detected: {results['anomaly_count']} / {results['n_samples']}")
    
    if output_path:
        # Load full data with predictions
        with open(features_json_path, 'r') as f:
            features = json.load(f)
        
        df = pd.DataFrame(features)
        result_df = predictor.predict_and_label(df)
        
        # Convert to JSON-serializable format
        output_data = result_df.to_dict(orient='records')
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        logger.info(f"Results saved to {output_path}")
    
    return results
