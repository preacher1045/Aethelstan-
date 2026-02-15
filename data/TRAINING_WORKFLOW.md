# Training Data Management

## Current Status

### Local Captures (In Progress)
Location: `data/raw/local_captures/`

| File | Size | Status |
|------|------|--------|
| Capture_29_02_2026-01.pcapng | 23.9 MB | ⏳ Extracting |
| Capture_28_01_2026.pcapng | 236.2 MB | ⏳ Pending |
| Capture_31_01_2026_001.pcapng | 340.9 MB | ⏳ Pending |
| capture_31_01_2026.pcapng | 923.7 MB | ⏳ Pending |

**Total:** ~1.5 GB of local traffic

### Enterprise Captures (Planned)
- 5-6 enterprise-level PCAPs (awaiting upload)

---

## Workflow

### 0. Convert PCAPNG Files (If Needed)

If your captures are in `.pcapng` format, convert them first:

```python
python scripts\convert_pcapng_to_pcap.py
```

This creates `.pcap` versions in `data/raw/local_captures_converted/`

### 1. Extract Features from New PCAPs

#### Option A: Single File
```powershell
.\backend\features\rust_extractor\target\release\rust_extractor.exe `
  "data\raw\<your_file>.pcapng" `
  "data\processed\<dataset_name>\<your_file>_features.json"
```

#### Option B: Batch Processing
```python
# Add PCAPs to data/raw/<dataset_name>/
python scripts/batch_extract_features.py
```

### 2. Combine Datasets

After extracting features from multiple files:

```python
python scripts/combine_datasets.py
```

This creates:
- `data/training/local_captures_combined.json` - All local captures
- `data/training/enterprise_captures_combined.json` - All enterprise data
- Metadata files with source tracking

### 3. Train Model

#### Option A: Train on Local Captures Only
```python
python scripts/train_on_local_captures.py
```

#### Option B: Train on All Data (After Adding Enterprise)
```python
python scripts/train_model.py
```

---

## Directory Structure

```
data/
├── raw/                          # Original PCAP files
│   ├── local_captures/           # Your local network captures
│   └── enterprise_captures/      # Enterprise-level PCAPs (future)
│
├── processed/                    # Extracted features (JSON)
│   ├── local_captures/
│   │   ├── file1_features.json
│   │   └── file2_features.json
│   └── enterprise_captures/
│
├── training/                     # Combined datasets for training
│   ├── local_captures_combined.json
│   ├── enterprise_captures_combined.json
│   └── all_data_combined.json
│
└── baselines/                    # Normal traffic baselines
    └── 2023_all_traffic_baseline.json
```

---

## Adding Enterprise Data (Future)

When you receive enterprise PCAPs:

1. **Create directory:**
   ```powershell
   New-Item -ItemType Directory -Path "data\raw\enterprise_captures"
   ```

2. **Copy PCAPs:**
   ```powershell
   Copy-Item "<path_to_enterprise_pcaps>\*" "data\raw\enterprise_captures\"
   ```

3. **Extract features:**
   ```python
   # Update batch_extract_features.py to point to enterprise_captures
   python scripts/batch_extract_features.py
   ```

4. **Combine all datasets:**
   ```python
   python scripts/combine_datasets.py  # Creates combined files
   ```

5. **Retrain model:**
   ```python
   python scripts/train_model.py
   ```

---

## Model Versions

Track different model versions based on training data:

| Version | Training Data | Windows | File |
|---------|--------------|---------|------|
| v0.1 | Single 2023 PCAP | 91 | `network_anomaly_model.pkl` (overfitted) |
| v0.2 | Local captures (4 files) | TBD | `network_anomaly_model_local.pkl` |
| v1.0 | Local + Enterprise | TBD | `network_anomaly_model_v1.pkl` |

---

## Data Quality Guidelines

### Known-Good (Normal) Traffic Characteristics:
- Regular office hours traffic
- Standard protocols (HTTP/S, DNS, SSH)
- No port scans or brute force attempts
- Typical packet rates for network type

### Attack/Anomalous Traffic (For Testing):
- DDoS patterns
- Port scanning
- Unusual protocol ratios
- Suspicious data exfiltration
- Brute force login attempts

---

## Next Steps

1. ✅ Extract features from 4 local captures
2. ⏳ Train model on local data
3. ⏳ Acquire 5-6 enterprise PCAPs
4. ⏳ Extract and combine enterprise data
5. ⏳ Retrain model on full dataset
6. ⏳ Implement multi-stage pipeline (statistical gate + ML)
7. ⏳ Acquire labeled attack samples for evaluation

---

## Notes

- **Window size:** 10 seconds (configured in Rust extractor)
- **Expected windows:** ~1000-2000 from all local + enterprise data
- **Contamination parameter:** Currently 0.05 (5% expected anomalies)
- **Feature count:** 24 features after cleaning/engineering

---

## Troubleshooting

### Extraction takes too long
- Large PCAPs (>500MB) can take 10+ minutes
- Run in background or use Task Scheduler
- Consider splitting very large files

### Low window count
- Check PCAP duration (needs >100s for 10 windows)
- Verify PCAP isn't corrupted
- Check Rust extractor output for errors

### Model still overfitting
- Need more diverse data sources
- Consider implementing statistical gate (Stage 1)
- Tune contamination parameter
