"""
Model management for deployment.

This script ensures the production model is available:
1. Checks if production model exists
2. If missing, provides instructions to train or download
3. Can be run during deployment/initialization
"""

import sys
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_production_model():
    """Check if production model exists."""
    base_dir = Path(__file__).parent.parent
    model_path = base_dir / "models" / "network_anomaly_model_combined.pkl"
    
    if model_path.exists():
        size_mb = model_path.stat().st_size / (1024 * 1024)
        logger.info(f"✓ Production model found: {model_path}")
        logger.info(f"  Size: {size_mb:.2f} MB")
        return True
    else:
        logger.error(f"✗ Production model NOT found: {model_path}")
        return False


def get_model_info():
    """Get information about available models."""
    base_dir = Path(__file__).parent.parent
    models_dir = base_dir / "models"
    
    if not models_dir.exists():
        logger.error(f"Models directory not found: {models_dir}")
        return []
    
    models = []
    for model_file in models_dir.glob("*.pkl"):
        size_mb = model_file.stat().st_size / (1024 * 1024)
        models.append({
            'name': model_file.name,
            'path': model_file,
            'size_mb': size_mb
        })
    
    return models


def ensure_production_model():
    """
    Ensure production model is available for deployment.
    
    Returns:
        bool: True if model is available, False otherwise
    """
    print("\n" + "="*80)
    print("PRODUCTION MODEL CHECK")
    print("="*80 + "\n")
    
    if check_production_model():
        print("\n✓ Production model is ready for deployment!")
        print("="*80 + "\n")
        return True
    
    print("\n⚠️  WARNING: Production model is missing!")
    print("\nAvailable options:")
    print("\n1. Train the production model:")
    print("   python scripts/train_model_combined.py")
    print("\n2. If you have training data elsewhere, copy the model file:")
    print("   models/network_anomaly_model_combined.pkl")
    
    print("\n3. Alternative: Use model from cloud storage (for production deployment):")
    print("   - Upload model to cloud storage (S3, Azure Blob, etc.)")
    print("   - Download during deployment initialization")
    
    print("\nCurrent models in models/ directory:")
    models = get_model_info()
    if models:
        for model in models:
            print(f"  • {model['name']:<40} {model['size_mb']:>8.2f} MB")
    else:
        print("  (none)")
    
    print("\n" + "="*80 + "\n")
    return False


def download_model_from_url(url, destination=None):
    """
    Download model from URL (for deployment scenarios).
    
    Parameters:
        url (str): URL to download model from
        destination (Path, optional): Where to save. Defaults to production model path.
    
    Returns:
        bool: True if successful
    """
    import urllib.request
    
    base_dir = Path(__file__).parent.parent
    if destination is None:
        destination = base_dir / "models" / "network_anomaly_model_combined.pkl"
    
    try:
        logger.info(f"Downloading model from: {url}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        urllib.request.urlretrieve(url, destination)
        
        size_mb = destination.stat().st_size / (1024 * 1024)
        logger.info(f"✓ Model downloaded successfully: {destination}")
        logger.info(f"  Size: {size_mb:.2f} MB")
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to download model: {e}")
        return False


if __name__ == "__main__":
    # Check for production model
    if not ensure_production_model():
        sys.exit(1)
    
    sys.exit(0)
