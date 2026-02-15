# Project Structure

```
refactored_project/
├── README.md                          # Main project documentation
├── requirements.txt                   # Python dependencies
│
├── .git/                              # Git version control
├── .gitignore                         # Git ignore rules
├── .venv/                             # Python virtual environment
│
├── backend/                           # Core application backend
│   ├── __pycache__/
│   ├── app.py                         # Flask/FastAPI main application
│   ├── config.py                      # Configuration settings
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py                  # API endpoints
│   ├── features/
│   │   ├── extractor.py               # Python feature extraction wrapper
│   │   └── rust_extractor/            # Rust-based PCAP feature extractor
│   │       ├── cargo.toml
│   │       ├── src/
│   │       └── main.rs
│   ├── ingestion/
│   │   ├── __init__.py
│   │   └── pcap_loader.py             # PCAP file loading
│   ├── insight/
│   │   ├── __init__.py
│   │   └── generator.py               # Alert/insight generation
│   ├── ml/
│   │   ├── __init__.py
│   │   ├── inference.py               # Model inference pipeline
│   │   ├── model.py                   # Model training logic
│   │   └── production_inference.py    # Production inference wrapper
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── database.py                # Database interactions
│   │   └── repository.py              # Data repository
│   └── utils/
│       ├── __init__.py
│       └── helper.py                  # Utility functions
│
├── frontend/                          # Next.js web interface
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.ts
│   ├── eslint.config.mjs
│   ├── postcss.config.mjs
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── globals.css
│   └── public/
│
├── data/                              # Data storage
│   ├── raw/                           # Raw PCAP files and data
│   │   ├── test_large.pcap
│   │   ├── split_merged_50M/          # Split chunks from large PCAP
│   │   └── [other PCAP files]
│   └── processed/                     # Processed features
│       ├── training_data_consolidated.json
│       ├── test_net_traffic_features.json
│       ├── 2023_test_features.json
│       ├── window_features.json
│       └── [feature JSON files]
│
├── models/                            # Trained ML models
│   ├── network_anomaly_model_combined.pkl
│   ├── network_anomaly_model_scale_robust.pkl
│   ├── network_anomaly_model_behavioral.pkl
│   ├── scale_robust_features_config.json
│   └── behavioral_features_config.json
│
├── docs/                              # Documentation and outputs
│   ├── model_insight/                 # Model inference results
│   │   ├── behavioral_model_predictions.json
│   │   ├── behavioral_model_anomaly_drivers.json
│   │   ├── behavioral_model_insights.json
│   │   ├── behavioral_model_inference_results.png
│   │   ├── behavioral_model_diagnostics.png
│   │   ├── BEHAVIORAL_MODEL_INFERENCE_REPORT.md
│   │   ├── DISTRIBUTION_COMPARISON_REPORT.md
│   │   ├── feature_distribution_comparison.png
│   │   └── [other analysis outputs]
│   └── README.md                      # Docs readme
│
├── scripts/                           # Standalone Python scripts
│   ├── benchmark.py                   # Performance benchmarking
│   ├── train_model.py                 # Model training script
│   ├── test_extractor.py              # Extractor testing
│   ├── process_large_pcap.py          # Large PCAP processing pipeline
│   ├── compare_feature_distributions.py  # Distribution comparison
│   ├── consolidate_training_data.py   # Data consolidation
│   ├── retrain_scale_robust.py        # Scale-robust model retraining
│   ├── train_behavioral_model.py      # Behavioral model training
│   └── infer_behavioral_model.py      # Behavioral model inference
│
├── tests/                             # Test files (organized)
│   ├── check_duration.py
│   ├── quick_test.py
│   ├── test_2023_pcap.py
│   ├── test_baseline_calculator.py
│   ├── test_inference.py
│   ├── test_new_model.py
│   └── test_system.py
│
├── utils/                             # Utility scripts (organized)
│   ├── regenerate_scores.py
│   └── extract_all_local.ps1
│
└── config/                            # Configuration files (reserved)
```

## Key Directories Explained

### `backend/`
Core Python application with modular components:
- **api/**: REST API endpoints
- **features/**: Feature extraction (Python wrapper + Rust binary)
- **ml/**: Machine learning pipeline (training, inference, models)
- **storage/**: Data persistence layer
- **insight/**: Alert and insight generation

### `data/`
- **raw/**: Original PCAP captures and split chunks
- **processed/**: Extracted features in JSON format

### `models/`
Trained ML models:
- `network_anomaly_model_combined.pkl` - Original volume-based model
- `network_anomaly_model_scale_robust.pkl` - Mixed scale-robust features
- `network_anomaly_model_behavioral.pkl` - Pure behavioral model (recommended)

### `docs/model_insight/`
Model inference results, visualizations, and reports
- Predictions and anomaly drivers
- PNG visualizations (timelines, distributions)
- Analysis reports

### `scripts/`
Standalone processing scripts for:
- Model training and retraining
- Feature engineering
- Large PCAP processing
- Inference runs

### `tests/`
Test and validation scripts (now organized)

### `utils/`
Helper scripts for maintenance and utilities

## Current Status

✅ **Models Available:**
- **Behavioral Model** (recommended): `network_anomaly_model_behavioral.pkl`
  - 12 behavioral features (no volume dominance)
  - 12.1% anomaly rate on test data
  - Scale-independent and interpretable

✅ **Latest Analysis:**
- Inference on 107-window merged_50M.pcap dataset
- 13 anomalies identified with specific drivers
- Feature distribution analysis complete
- Sanity checks all passing

✅ **Documentation:**
- Complete inference report
- Anomaly drivers exported
- Visualizations generated
- Distribution comparison available
