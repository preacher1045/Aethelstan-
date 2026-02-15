# Model Deployment Guide

## Strategy: Which Models to Commit to GitHub?

### ✅ COMMIT (Keep in Git)
- **network_anomaly_model_combined.pkl** - Production model
  - Small size (typically <10 MB for IsolationForest)
  - Essential for deployment
  - Trained on 1,988 windows

### ❌ IGNORE (Don't commit)
- Experimental/test models
- Old model versions
- Training checkpoints
- Models >100 MB (use Git LFS or cloud storage)

---

## Deployment Options

### Option 1: Commit Model to Git ✅ (Recommended for Small Models)

**Current Setup**: Production model is committed to repository

**Pros:**
- Simple deployment
- Version controlled with code
- No extra infrastructure needed

**Cons:**
- Only works for small models (<100 MB)
- Increases repo size over time

**Usage:**
```bash
git clone <repo>
cd refactored_project
python scripts/ensure_model.py  # Verify model exists
python backend/app.py            # Start application
```

---

### Option 2: Git LFS (Large File Storage) - For 100MB-1GB Models

**Setup:**
```bash
# Install Git LFS
git lfs install

# Track model files
git lfs track "models/*.pkl"
git add .gitattributes

# Commit and push
git add models/network_anomaly_model_combined.pkl
git commit -m "Add production model via LFS"
git push
```

**Pros:**
- Handles larger files
- Still version controlled
- Free up to 1 GB on GitHub

**Cons:**
- Requires Git LFS setup
- Bandwidth limits on free tier

---

### Option 3: Cloud Storage - For Very Large Models (>1GB)

**AWS S3 Example:**

1. **Upload model to S3:**
```bash
aws s3 cp models/network_anomaly_model_combined.pkl \
  s3://your-bucket/models/network_anomaly_model_combined.pkl
```

2. **Download during deployment:**
```python
# In startup script or ensure_model.py
from scripts.ensure_model import download_model_from_url

MODEL_URL = "https://your-bucket.s3.amazonaws.com/models/network_anomaly_model_combined.pkl"
download_model_from_url(MODEL_URL)
```

3. **Update deployment script:**
```bash
#!/bin/bash
# deploy.sh

# Download model
python scripts/ensure_model.py --download-url $MODEL_URL

# Start application
python backend/app.py
```

**Pros:**
- No size limits
- Fast CDN distribution
- Can serve different models per environment

**Cons:**
- Extra infrastructure cost
- More complex deployment

---

### Option 4: Train on Deployment (CI/CD Pipeline)

**For reproducible training:**

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Python
        uses: actions/setup-python@v2
        
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Check if model exists
        run: python scripts/ensure_model.py || echo "Model missing"
      
      - name: Train model if missing (optional)
        run: |
          if [ ! -f models/network_anomaly_model_combined.pkl ]; then
            python scripts/train_model_combined.py
          fi
      
      - name: Deploy
        run: ./deploy.sh
```

**Pros:**
- Reproducible
- No model storage needed
- Always fresh model

**Cons:**
- Requires training data in repo or accessible
- Longer deployment time
- Needs compute resources

---

## Recommended Setup for Your Project

### Current Model Size Check:
```bash
python scripts/ensure_model.py
```

### Recommendation:

**If model <100 MB** → **Option 1** (Commit to Git) ✅
- Simple, no extra setup
- Perfect for small ML models
- Your IsolationForest model is likely <10 MB

**If model 100MB-1GB** → **Option 2** (Git LFS)

**If model >1GB** → **Option 3** (Cloud Storage)

---

## Quick Deployment Checklist

### For Development:
```bash
# 1. Clone repo
git clone <repo>

# 2. Setup environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# 3. Verify model
python scripts/ensure_model.py

# 4. Run tests
python -m pytest

# 5. Start app
python backend/app.py
```

### For Production (Docker Example):
```dockerfile
FROM python:3.13

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY . .

# Verify model exists (fails build if missing)
RUN python scripts/ensure_model.py

# Start application
CMD ["python", "backend/app.py"]
```

---

## Environment Variables (Optional)

Create `.env` file for flexible model loading:

```bash
# .env
MODEL_PATH=models/network_anomaly_model_combined.pkl
MODEL_DOWNLOAD_URL=https://your-cdn.com/models/latest.pkl
AUTO_DOWNLOAD_MODEL=true
```

---

## Model Versioning Best Practices

1. **Semantic versioning for models:**
   - `network_anomaly_model_v1.0.0.pkl`
   - `network_anomaly_model_v1.1.0.pkl`

2. **Tag releases:**
   ```bash
   git tag -a v1.0.0 -m "Release with model v1.0.0"
   git push origin v1.0.0
   ```

3. **Model registry (advanced):**
   - MLflow Model Registry
   - DVC (Data Version Control)
   - Weights & Biases

---

## Summary

**Your Current Setup:**
- ✅ Production model committed to Git
- ✅ Old/experimental models ignored
- ✅ `ensure_model.py` verifies model availability
- ✅ Ready for simple deployment

**No changes needed unless:**
- Model grows >100 MB (switch to Git LFS)
- Multiple environments need different models (use cloud storage)
- Training is fast and reproducible (train on deployment)
