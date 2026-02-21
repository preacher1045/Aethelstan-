import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# -------------------------------------------------------------------
# Base Paths
# -------------------------------------------------------------------
BASE_DIR = Path(__file__).parent.parent  # root of the project

# -------------------------------------------------------------------
# Database
# -------------------------------------------------------------------
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

# -------------------------------------------------------------------
# File Storage
# -------------------------------------------------------------------
UPLOAD_DIR = BASE_DIR / "data" / "uploads"      # where PCAP files are saved
PROCESSED_DIR = BASE_DIR / "data" / "processed" # where feature JSONs are saved
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------------
# Rust Extractor
# -------------------------------------------------------------------
RUST_BINARY = BASE_DIR / "backend" / "features" / "rust_extractor" / "target" / "release" / "rust_extractor"

# -------------------------------------------------------------------
# ML Model
# -------------------------------------------------------------------
MODEL_PATH = BASE_DIR / "models" / "network_anomaly_model_combined.pkl"

# -------------------------------------------------------------------
# App Settings
# -------------------------------------------------------------------
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", 4096)) # default 4GB
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

