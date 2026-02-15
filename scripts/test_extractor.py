import sys
from pathlib import Path
import time

# Add project root to PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from backend.features.extractor import PacketFeatureExtractor

def run_extractor_test():
    print("=" * 60)
    print("🚦 Packet Feature Extractor – Chunked Test Started")
    print("=" * 60)

    pcap_path = Path("data/raw/test_large.pcap")
    if not pcap_path.exists():
        print(f"❌ PCAP file not found: {pcap_path}")
        return

    print(f"📁 Using PCAP file: {pcap_path}")
    print("🧪 Initializing extractor...")

    extractor = PacketFeatureExtractor(str(pcap_path), window_size=60)
    output_file = Path("data/processed/test_large.features.jsonl")

    start_time = time.perf_counter()
    extractor.write_features_to_file(str(output_file), chunk_size=1000)
    end_time = time.perf_counter()
    duration = end_time - start_time

    print("-" * 60)
    print(f"⏱️  Total extraction time: {duration:.2f} seconds")
    print("=" * 60)
    print("🏁 Test Finished")
    print("=" * 60)

if __name__ == "__main__":
    run_extractor_test()
