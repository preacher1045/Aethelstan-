"""
Process a large PCAP: split (if large), extract features via Rust extractor,
merge feature JSONs, run inference, generate insights and two visualizations
(academic + professional). Saves outputs in `docs/model_insight/`.

Usage:
    python scripts/process_large_pcap.py --pcap data/raw/merged_50M.pcap

Notes:
- Uses Scapy for streaming read and writing chunks (memory efficient).
- Calls `backend/features/rust_extractor/target/release/rust_extractor.exe` for feature extraction.
- If Rust extractor missing, script will error and explain how to build it.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
import time

# Use non-interactive backend
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

# Add repo root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from backend.ml.production_inference import predict_with_feature_engineering
from backend.insight.generator import InsightGenerator

try:
    from scapy.utils import RawPcapReader, PcapWriter
except Exception as e:
    raise RuntimeError("Scapy is required for splitting PCAPs. Install via 'pip install scapy'")

CHUNK_CHECK_INTERVAL = 10000  # check file size every N packets


def split_pcap_stream(in_pcap: Path, out_dir: Path, chunk_size_mb: int = 500):
    """Split `in_pcap` into chunk files no larger than chunk_size_mb.
    Returns list of chunk file paths.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    chunk_paths = []
    chunk_idx = 0
    writer = None
    current_chunk_path = None
    pkt_in_chunk = 0
    chunk_size_bytes = chunk_size_mb * 1024 * 1024

    reader = RawPcapReader(str(in_pcap))
    try:
        # Try to obtain linktype from the pcap reader if available
        reader_linktype = getattr(reader, 'linktype', None)
        # Fallback linktype (1 == DLT_EN10MB / Ethernet)
        if reader_linktype is None:
            reader_linktype = 1
        for i, pkt_data in enumerate(reader):
            # RawPcapReader yields bytes or (pkt, meta) depending on scapy version
            pkt_bytes = pkt_data[0] if isinstance(pkt_data, tuple) else pkt_data

            if writer is None:
                chunk_idx += 1
                current_chunk_path = out_dir / f"{in_pcap.stem}_part{chunk_idx}.pcap"
                # Use the same linktype as the input pcap when available to avoid
                # PcapWriter warnings about unknown link-layer types. This prevents
                # repeated "unknown LL type for bytes" messages and ensures correct
                # pcap headers for downstream tools.
                writer = PcapWriter(str(current_chunk_path), append=False, sync=True, linktype=reader_linktype)
                pkt_in_chunk = 0

            writer.write(pkt_bytes)
            pkt_in_chunk += 1

            # Periodically check chunk size to avoid expensive os.stat per packet
            if pkt_in_chunk % CHUNK_CHECK_INTERVAL == 0:
                try:
                    size = current_chunk_path.stat().st_size
                except FileNotFoundError:
                    size = 0
                if size >= chunk_size_bytes:
                    writer.close()
                    chunk_paths.append(current_chunk_path)
                    writer = None
                    current_chunk_path = None
                    pkt_in_chunk = 0
        # end for
    finally:
        if writer is not None:
            writer.close()
            chunk_paths.append(current_chunk_path)
        try:
            reader.close()
        except Exception:
            pass

    return chunk_paths


def run_rust_extractor(pcap_path: Path, output_json: Path):
    extractor_path = ROOT / 'backend' / 'features' / 'rust_extractor' / 'target' / 'release' / 'rust_extractor.exe'
    if not extractor_path.exists():
        raise FileNotFoundError(f"Rust extractor not found at {extractor_path}. Build it with `cargo build --release` in backend/features/rust_extractor`.")

    output_json.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(extractor_path), str(pcap_path), str(output_json)]
    print(f"Running extractor: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stdout)
        print(res.stderr)
        raise RuntimeError(f"Extractor failed on {pcap_path}")
    print(res.stdout)
    return output_json


def merge_feature_jsons(json_paths, merged_path: Path):
    merged = []
    for p in json_paths:
        with open(p, 'r') as f:
            data = json.load(f)
        if isinstance(data, list):
            merged.extend(data)
        else:
            # single-record JSON
            merged.append(data)
    merged_path.parent.mkdir(parents=True, exist_ok=True)
    with open(merged_path, 'w') as f:
        json.dump(merged, f)
    return merged_path


def generate_visualizations_academic(df, results, insights, out_dir: Path, name_stem: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    sns.set(style='whitegrid')

    scores = results['scores']
    preds = results['predictions']

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    sns.histplot(scores, kde=True, ax=axes[0,0], color='navy')
    axes[0,0].set_title('Anomaly Score Distribution (Academic)')

    sns.boxplot(x=preds, y=scores, ax=axes[0,1])
    axes[0,1].set_xlabel('Prediction (1 normal, -1 anomaly)')
    axes[0,1].set_title('Scores by Class')

    axes[1,0].scatter(df['packet_count'], scores, alpha=0.4)
    axes[1,0].set_xlabel('Packet Count')
    axes[1,0].set_ylabel('Anomaly Score')
    axes[1,0].set_title('Packet Count vs Score')

    axes[1,1].plot(scores, marker='o', linewidth=0.8)
    axes[1,1].set_title('Anomaly Score Timeline')

    plt.tight_layout()
    out_file = out_dir / f"{name_stem}_academic.png"
    plt.savefig(out_file, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved academic visualization: {out_file}")
    return out_file


def generate_visualizations_professional(df, results, insights, out_dir: Path, name_stem: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    plt.style.use('seaborn-darkgrid')

    scores = results['scores']
    preds = results['predictions']

    fig = plt.figure(constrained_layout=True, figsize=(16,8))
    gs = fig.add_gridspec(2, 3)

    ax_hist = fig.add_subplot(gs[0,0])
    ax_box = fig.add_subplot(gs[0,1])
    ax_scatter = fig.add_subplot(gs[0,2])
    ax_timeline = fig.add_subplot(gs[1,:])

    ax_hist.hist(scores, bins=40, color='#2E86AB')
    ax_hist.set_title('Score Distribution')

    ax_box.boxplot([scores[preds==1], scores[preds==-1]], labels=['Normal','Anomaly'], patch_artist=True,
                   boxprops=dict(facecolor='#8AB6D6'))
    ax_box.set_title('Normal vs Anomaly')

    cmap = {1:'#2ecc71', -1:'#e74c3c'}
    colors = [cmap[int(p)] for p in preds]
    ax_scatter.scatter(df['avg_packet_size'], df['bytes_per_sec'], c=colors, alpha=0.6)
    ax_scatter.set_xlabel('Avg Packet Size')
    ax_scatter.set_ylabel('Bytes/sec')
    ax_scatter.set_title('Packet Size vs Throughput')

    ax_timeline.plot(results['scores'], linewidth=1.2, color='#1f77b4')
    ax_timeline.fill_between(range(len(scores)), results['scores'], alpha=0.1)
    ax_timeline.set_title('Anomaly Score Timeline')

    out_file = out_dir / f"{name_stem}_professional.png"
    plt.savefig(out_file, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved professional visualization: {out_file}")
    return out_file


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pcap', required=True, help='Path to PCAP file')
    parser.add_argument('--chunk-mb', type=int, default=500, help='Chunk size in MB')
    args = parser.parse_args()

    pcap = Path(args.pcap)
    if not pcap.exists():
        print(f"PCAP not found: {pcap}")
        sys.exit(1)

    out_dir = ROOT / 'docs' / 'model_insight'
    temp_chunks_dir = ROOT / 'data' / 'raw' / f'split_{pcap.stem}'
    temp_features_dir = ROOT / 'data' / 'processed' / f'split_features_{pcap.stem}'
    merged_features = out_dir / f"{pcap.stem}_features.json"

    # 1) If file >= 1GB, split; otherwise just use file
    size_bytes = pcap.stat().st_size
    print(f"PCAP size: {size_bytes/(1024*1024):.2f} MB")

    if size_bytes >= (1 * 1024 * 1024 * 1024):
        print("Large file detected. Splitting into chunks...")
        chunks = split_pcap_stream(pcap, temp_chunks_dir, chunk_size_mb=args.chunk_mb)
    else:
        chunks = [pcap]

    print(f"Chunks to process: {len(chunks)}")

    # 2) Run extractor on each chunk
    feature_files = []
    for idx, c in enumerate(chunks, 1):
        out_json = temp_features_dir / f"{c.stem}_features.json"
        out_json.parent.mkdir(parents=True, exist_ok=True)
        print(f"Extracting chunk {idx}/{len(chunks)}: {c.name}")
        run_rust_extractor(c, out_json)
        feature_files.append(out_json)

    # 3) Merge features
    print("Merging feature JSONs...")
    merge_feature_jsons(feature_files, merged_features)
    print(f"Merged features saved to: {merged_features}")

    # 4) Run inference & insights
    print("Running inference and generating insights...")
    results = predict_with_feature_engineering(str(merged_features))
    generator = InsightGenerator(max_alerts=10)
    records = results['detailed_results'].to_dict('records')
    insights = generator.generate(records)

    # Save outputs
    insights_file = out_dir / f"{pcap.stem}_insights.json"
    with open(insights_file, 'w') as f:
        json.dump(insights, f, indent=2)
    preds_file = out_dir / f"{pcap.stem}_predictions.json"
    with open(preds_file, 'w') as f:
        json.dump(results['detailed_results'].to_dict('records'), f, indent=2)

    # 5) Visualizations
    print("Creating visualizations (academic & professional)...")
    df = results['detailed_results']
    generate_visualizations_academic(df, results, insights, out_dir, pcap.stem)
    generate_visualizations_professional(df, results, insights, out_dir, pcap.stem)

    # 6) Summary report
    report_path = out_dir / f"ANALYSIS_REPORT_{pcap.stem}.md"
    with open(report_path, 'w') as f:
        f.write(f"# Analysis Report - {pcap.name}\n\n")
        f.write(f"Processed at: {time.ctime()}\n\n")
        f.write(json.dumps(insights, indent=2))

    print("All done. Outputs in:", out_dir)

if __name__ == '__main__':
    main()
