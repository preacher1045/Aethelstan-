"""
Production-ready inference utilities with feature engineering pipeline.
"""

import json
import sys
from pathlib import Path
import logging
import numpy as np

logger = logging.getLogger(__name__)


def calculate_contributing_features(df_features, predictions, scores, top_n=5):
    """
    Calculate which features contributed most to each anomaly detection.
    For Isolation Forest, we use feature deviation from median as a proxy for contribution.
    
    Parameters:
        df_features (DataFrame): Engineered features used for prediction
        predictions (array): Anomaly predictions (-1 for anomaly, 1 for normal)
        scores (array): Anomaly scores (lower = more anomalous)
        top_n (int): Number of top contributing features to return
        
    Returns:
        list: List of dicts with contributing features for each sample
    """
    import pandas as pd
    
    # Calculate feature medians and MADs (Median Absolute Deviation)
    medians = df_features.median()
    mads = (df_features - medians).abs().median()
    
    contributing_features_list = []
    
    for idx in range(len(df_features)):
        if predictions[idx] == -1:  # Only for anomalies
            # Calculate deviation from median for each feature
            deviations = {}
            for col in df_features.columns:
                value = df_features.iloc[idx][col]
                median = medians[col]
                mad = mads[col] if mads[col] > 0 else 1
                # Normalized deviation
                deviation = abs(value - median) / mad
                deviations[col] = deviation
            
            # Sort by deviation and take top N
            top_features = sorted(deviations.items(), key=lambda x: x[1], reverse=True)[:top_n]
            
            # Normalize to percentages that sum to ~100
            total_deviation = sum(dev for _, dev in top_features)
            if total_deviation > 0:
                contributing_features = {
                    feat: round((dev / total_deviation) * 100, 1) 
                    for feat, dev in top_features
                }
            else:
                contributing_features = {}
            
            contributing_features_list.append(contributing_features)
        else:
            # Not an anomaly
            contributing_features_list.append({})
    
    return contributing_features_list


def predict_with_feature_engineering(pcap_features_json, model_path=None):
    """
    Production-ready inference with complete feature engineering pipeline.
    
    This is the main function to use in production - it handles:
    1. Loading raw features from Rust extractor
    2. Feature engineering (same as training)
    3. Anomaly detection with trained model
    
    Parameters:
        pcap_features_json (str): Path to JSON file with raw features from Rust extractor
        model_path (str, optional): Path to model file. If None, uses production model.
        
    Returns:
        dict: Predictions with summary statistics
    """
    import pandas as pd
    
    # Add scripts to path for data_cleanup
    base_dir = Path(__file__).parent.parent.parent
    scripts_path = base_dir / "scripts"
    if str(scripts_path) not in sys.path:
        sys.path.insert(0, str(scripts_path))
    
    from data_cleanup import clean_and_engineer_features, select_features
    from backend.ml.inference import AnomalyPredictor
    
    # Load raw features
    with open(pcap_features_json, 'r') as f:
        raw_data = json.load(f)
    
    df_raw = pd.DataFrame(raw_data)
    logger.info(f"Loaded {len(df_raw)} windows from {pcap_features_json}")
    
    # Feature engineering (same as training)
    df_engineered = clean_and_engineer_features(df_raw)
    
    # Load model so we can align to its required feature list when available
    predictor = AnomalyPredictor(model_path)
    feature_list = predictor.feature_names if getattr(predictor, "feature_names", None) else None
    df_features = select_features(df_engineered, feature_list)
    logger.info(f"Feature engineering complete: {df_features.shape}")
    
    # Predict using only model-required fields
    results = predictor.predict_from_features(df_features)
    
    # Add metadata
    results['n_samples'] = len(df_features)
    results['features_file'] = str(pcap_features_json)
    results['anomaly_percentage'] = results['anomaly_ratio'] * 100
    
    # Create detailed results with original data + predictions
    df_results = df_raw.copy()
    df_results['anomaly'] = results['predictions']
    df_results['anomaly_score'] = results['scores']
    df_results['is_anomaly'] = df_results['anomaly'] == -1
    
    # Calculate contributing features for each sample
    contributing_features_list = calculate_contributing_features(
        df_features, 
        results['predictions'], 
        results['scores']
    )
    df_results['contributing_features'] = contributing_features_list
    
    results['detailed_results'] = df_results
    
    logger.info(f"Anomalies detected: {results['anomaly_count']}/{results['n_samples']} ({results['anomaly_percentage']:.1f}%)")
    
    return results


def quick_predict(pcap_features_json):
    """
    Quick prediction using production model with nice output.
    
    Parameters:
        pcap_features_json (str): Path to features JSON from Rust extractor
        
    Returns:
        DataFrame: Results with anomaly labels
    """
    results = predict_with_feature_engineering(pcap_features_json)
    
    print(f"\n{'='*80}")
    print(f"ANOMALY DETECTION RESULTS")
    print(f"{'='*80}")
    print(f"  File: {Path(pcap_features_json).name}")
    print(f"  Windows analyzed: {results['n_samples']}")
    print(f"  Anomalies detected: {results['anomaly_count']} ({results['anomaly_percentage']:.1f}%)")
    print(f"  Average anomaly score: {results['scores'].mean():.3f}")
    print(f"{'='*80}\n")
    
    if results['anomaly_count'] > 0:
        anomalies = results['detailed_results'][results['detailed_results']['is_anomaly']]
        print(f"Top anomalous windows (by score):")
        top_3 = anomalies.nsmallest(min(3, len(anomalies)), 'anomaly_score')
        for idx, row in top_3.iterrows():
            print(f"  • Window {idx}: score={row['anomaly_score']:.3f}, packets={row.get('packet_count', 'N/A')}, bytes={row.get('total_bytes', 'N/A')}")
        print()
    
    return results['detailed_results']
