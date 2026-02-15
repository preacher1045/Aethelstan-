# Script Classification for Deployment

## 🚀 KEEP FOR PRODUCTION (Essential)

### `ensure_model.py` ✅
- **Purpose**: Verify production model exists before starting app
- **Usage**: Run during deployment initialization
- **Keep**: YES - Critical for deployment safety

### `data_cleanup.py` ✅
- **Purpose**: Feature engineering pipeline (used by inference)
- **Usage**: Required by production_inference.py for preprocessing
- **Keep**: YES - Core functionality

---

## 🧪 REMOVE FOR PRODUCTION (Development/Testing Only)

### Training Scripts (Can retrain offline, not needed in production):

**`train_model.py`** ❌
- Purpose: Train original model
- Remove: YES - Training done offline

**`train_model_combined.py`** ❌
- Purpose: Train combined model
- Remove: YES - Model already trained and committed

**`train_on_local_captures.py`** ❌
- Purpose: Train on local data only
- Remove: YES - Superseded by combined model

---

### Data Preparation (Pre-deployment work):

**`batch_extract_features.py`** ❌
- Purpose: Batch extract features from multiple PCAPs
- Remove: YES - Feature extraction done before training

**`convert_pcapng_to_pcap.py`** ❌
- Purpose: Convert PCAPNG to PCAP format
- Remove: YES - One-time data preparation

**`combine_datasets.py`** ❌
- Purpose: Combine multiple datasets
- Remove: YES - Training data prep only

---

### Testing & Validation:

**`test_extractor.py`** ❌
- Purpose: Test Rust extractor during development
- Remove: YES - Development testing only

**`test_production_inference.py`** ❌
- Purpose: Test inference module
- Remove: YES - Unit testing, not needed in production

**`compare_all_models.py`** ❌
- Purpose: Compare model performance
- Remove: YES - Analysis/benchmarking only

**`labeled_evaluation.py`** ❌
- Purpose: Evaluate model on labeled attack data
- Remove: YES - Validation/research only

---

### Monitoring & Analysis (Development tools):

**`check_all_progress.py`** ❌
- Purpose: Monitor extraction progress
- Remove: YES - Development monitoring

**`check_extraction_progress.py`** ❌
- Purpose: Check feature extraction status
- Remove: YES - Development monitoring

**`benchmark.py`** ❌
- Purpose: Benchmark performance
- Remove: YES - Performance testing only

**`baseline_calculator.py`** ❌
- Purpose: Calculate traffic baselines
- Remove: YES - Research/analysis tool

**`visualize_results.py`** ❌
- Purpose: Generate matplotlib charts
- Remove: YES - Analysis/reporting only

---

## 🗂️ ROOT DIRECTORY TEST FILES (Remove All)

**`check_duration.py`** ❌
**`quick_test.py`** ❌
**`regenerate_scores.py`** ❌
**`test_2023_pcap.py`** ❌
**`test_baseline_calculator.py`** ❌
**`test_inference.py`** ❌
**`test_new_model.py`** ❌
**`test_system.py`** ❌

All these are development/testing scripts.

---

## 📊 SUMMARY

### Production Bundle (Keep):
```
scripts/
├── ensure_model.py          ✅ Deployment safety
└── data_cleanup.py          ✅ Feature engineering pipeline
```

### Remove (14 files):
```
scripts/
├── baseline_calculator.py      ❌ Analysis
├── batch_extract_features.py   ❌ Data prep
├── benchmark.py                 ❌ Testing
├── check_all_progress.py       ❌ Monitoring
├── check_extraction_progress.py ❌ Monitoring
├── combine_datasets.py         ❌ Data prep
├── compare_all_models.py       ❌ Analysis
├── convert_pcapng_to_pcap.py   ❌ Data prep
├── labeled_evaluation.py       ❌ Validation
├── test_extractor.py           ❌ Testing
├── test_production_inference.py ❌ Testing
├── train_model.py              ❌ Training
├── train_model_combined.py     ❌ Training
├── train_on_local_captures.py  ❌ Training
└── visualize_results.py        ❌ Analysis

Root directory:
├── check_duration.py           ❌ Testing
├── quick_test.py               ❌ Testing
├── regenerate_scores.py        ❌ Analysis
├── test_*.py (5 files)         ❌ Testing
```

---

## 🎯 Action Plan

1. **Update .gitignore** to exclude development scripts
2. **Create deployment package** with only production files
3. **Keep full repo** for development (with all scripts)

---

## 💡 Best Practice

Instead of deleting, create a deployment configuration:

```python
# setup.py or pyproject.toml
[tool.poetry]
packages = [
    { include = "backend" },
    { include = "scripts", from = ".", only = ["ensure_model.py", "data_cleanup.py"] }
]
```

Or use a deployment script:
```bash
# deploy.sh
rsync -av --exclude='scripts/test_*.py' \
         --exclude='scripts/train_*.py' \
         --exclude='scripts/visualize_*.py' \
         . production/
```

This way you keep everything in development, but only deploy what's needed!
