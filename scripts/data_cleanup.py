"""
Data cleaning and preprocessing pipeline for network traffic features.
Converts Rust extractor output to ML-ready format.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_rust_output(json_file):
    """
    Load JSON output from Rust feature extractor.
    
    Parameters:
        json_file (str): Path to window_features.json
        
    Returns:
        DataFrame: Loaded features
    """
    with open(json_file, "r") as f:
        windows = json.load(f)
    
    df = pd.DataFrame(windows)
    logger.info(f"Loaded {len(df)} windows from {json_file}")
    return df


def clean_and_engineer_features(df):
    """
    Clean data and perform feature engineering.
    
    Parameters:
        df (DataFrame): Raw features from rust output
        
    Returns:
        DataFrame: Cleaned and engineered features
    """
    df = df.copy()
    
    # Handle division by zero
    df['packets_per_sec'] = df['packet_count'] / (df['window_end'] - df['window_start'])
    df['bytes_per_sec'] = df['total_bytes'] / (df['window_end'] - df['window_start'])
    
    # Ensure ratio columns exist and are valid
    total_packets = df['packet_count']
    df['tcp_ratio'] = np.divide(df['tcp_count'], total_packets, where=total_packets != 0, out=np.zeros_like(total_packets, dtype=float))
    df['udp_ratio'] = np.divide(df['udp_count'], total_packets, where=total_packets != 0, out=np.zeros_like(total_packets, dtype=float))
    df['icmp_ratio'] = np.divide(df['icmp_count'], total_packets, where=total_packets != 0, out=np.zeros_like(total_packets, dtype=float))
    df['other_ratio'] = np.divide(df['other_count'], total_packets, where=total_packets != 0, out=np.zeros_like(total_packets, dtype=float))
    
    # Entropy and diversity metrics
    df['protocol_entropy'] = -(
        df['tcp_ratio'] * np.log2(df['tcp_ratio'] + 1e-10) +
        df['udp_ratio'] * np.log2(df['udp_ratio'] + 1e-10) +
        df['icmp_ratio'] * np.log2(df['icmp_ratio'] + 1e-10) +
        df['other_ratio'] * np.log2(df['other_ratio'] + 1e-10)
    )
    
    # Additional engineered features
    df['ip_diversity'] = (df['unique_src_ips'] + df['unique_dst_ips']) / 2
    df['flow_density'] = np.divide(df['flow_count'], df['packet_count'], where=total_packets != 0, out=np.zeros_like(total_packets, dtype=float))
    
    # Fill any remaining NaN with 0
    df = df.fillna(0)
    
    # Remove infinite values
    df = df.replace([np.inf, -np.inf], 0)
    
    logger.info(f"Feature engineering complete. Shape: {df.shape}")
    return df


def remove_outliers(df, method='iqr', threshold=1.5):
    """
    Remove outlier rows using IQR or Z-score method.
    
    Parameters:
        df (DataFrame): Features with potential outliers
        method (str): 'iqr' or 'zscore'
        threshold (float): IQR multiplier or z-score threshold
        
    Returns:
        DataFrame: Data with outliers removed
    """
    df = df.copy()
    original_len = len(df)
    
    # Select only numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    
    if method == 'iqr':
        Q1 = df[numeric_cols].quantile(0.25)
        Q3 = df[numeric_cols].quantile(0.75)
        IQR = Q3 - Q1
        
        # Outliers are points outside Q1 - 1.5*IQR and Q3 + 1.5*IQR
        mask = ~((df[numeric_cols] < (Q1 - threshold * IQR)) | 
                 (df[numeric_cols] > (Q3 + threshold * IQR))).any(axis=1)
        df = df[mask]
    
    elif method == 'zscore':
        from scipy.stats import zscore
        z_scores = np.abs(zscore(df[numeric_cols]))
        df = df[(z_scores < threshold).all(axis=1)]
    
    removed = original_len - len(df)
    logger.info(f"Removed {removed} outliers. Remaining: {len(df)} samples")
    
    return df


def select_features(df, feature_list=None):
    """
    Select relevant features for ML model.
    
    Parameters:
        df (DataFrame): Full feature set
        feature_list (list, optional): Specific features to keep. If None, use defaults.
        
    Returns:
        DataFrame: Selected features only
    """
    if feature_list is None:
        # Default ML-relevant features
        feature_list = [
            'packet_count', 'total_bytes', 'avg_packet_size', 'min_packet_size', 'max_packet_size',
            'packet_size_std', 'tcp_count', 'udp_count', 'icmp_count', 'other_count',
            'tcp_ratio', 'udp_ratio', 'icmp_ratio', 'other_ratio',
            'unique_src_ips', 'unique_dst_ips', 'flow_count',
            'packets_per_sec', 'bytes_per_sec', 'protocol_entropy', 'ip_diversity',
            'flow_density', 'avg_flow_packets', 'avg_flow_bytes'
        ]
    
    # Keep only features that exist in df
    available = [f for f in feature_list if f in df.columns]
    
    logger.info(f"Selected {len(available)} features for ML")
    return df[available]


def normalize_features(df, method='minmax'):
    """
    Normalize numeric features.
    
    Parameters:
        df (DataFrame): Features to normalize
        method (str): 'minmax' or 'zscore'
        
    Returns:
        DataFrame: Normalized features
    """
    from sklearn.preprocessing import MinMaxScaler, StandardScaler
    
    df = df.copy()
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    
    if method == 'minmax':
        scaler = MinMaxScaler()
        df[numeric_cols] = scaler.fit_transform(df[numeric_cols])
    elif method == 'zscore':
        scaler = StandardScaler()
        df[numeric_cols] = scaler.fit_transform(df[numeric_cols])
    
    logger.info(f"Features normalized using {method} method")
    return df


def save_processed_data(df, output_path, formats=['csv']):
    """
    Save processed data in multiple formats.
    
    Parameters:
        df (DataFrame): Cleaned and engineered data
        output_path (str): Base path (without extension)
        formats (list): List of formats to save ('csv', 'parquet', 'json')
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    for fmt in formats:
        if fmt == 'csv':
            df.to_csv(f"{output_path}.csv", index=False)
            logger.info(f"Saved to {output_path}.csv")
        elif fmt == 'parquet':
            df.to_parquet(f"{output_path}.parquet", index=False)
            logger.info(f"Saved to {output_path}.parquet")
        elif fmt == 'json':
            df.to_json(f"{output_path}.json", orient='records', indent=2)
            logger.info(f"Saved to {output_path}.json")


def main(
    input_json="data/processed/window_features.json",
    output_path="data/processed/window_features_ml",
    remove_outliers_flag=False,
    normalize_flag=False,
    formats=['csv']
):
    """
    Main cleanup pipeline.
    
    Parameters:
        input_json (str): Path to rust output JSON
        output_path (str): Base path for output files
        remove_outliers_flag (bool): Whether to remove outliers
        normalize_flag (bool): Whether to normalize features
        formats (list): Output formats
    """
    # Load
    df = load_rust_output(input_json)
    
    # Clean and engineer
    df = clean_and_engineer_features(df)
    
    # Optional: remove outliers
    if remove_outliers_flag:
        df = remove_outliers(df, method='iqr', threshold=1.5)
    
    # Select features
    df = select_features(df)
    
    # Optional: normalize
    if normalize_flag:
        df = normalize_features(df, method='zscore')
    
    # Save
    save_processed_data(df, output_path, formats=formats)
    
    logger.info(f"✅ Pipeline complete! Processed data shape: {df.shape}")
    return df


if __name__ == "__main__":
    # Example usage
    df = main(
        input_json="data/processed/window_features.json",
        output_path="data/processed/window_features_ml",
        remove_outliers_flag=False,
        normalize_flag=False,
        formats=['csv', 'parquet']
    )
    print(df.head())

