"""Monitor extraction progress for all datasets."""
import json
from pathlib import Path
from datetime import datetime

def check_all_progress():
    base_dir = Path(__file__).parent.parent
    
    datasets = [
        {
            'name': 'Local Captures',
            'raw_dir': base_dir / "data" / "raw" / "local_captures_converted",
            'processed_dir': base_dir / "data" / "processed" / "local_captures"
        },
        {
            'name': 'Enterprise PCAPs',
            'raw_dir': base_dir / "data" / "raw" / "enterprise_pcap_files",
            'processed_dir': base_dir / "data" / "processed" / "enterprise_pcap_files"
        }
    ]
    
    print("\n" + "="*80)
    print(f"EXTRACTION PROGRESS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    grand_total_windows = 0
    
    for dataset in datasets:
        print(f"\n{dataset['name']}:")
        print("-" * 80)
        
        if not dataset['raw_dir'].exists():
            print(f"  ⚠️ Source directory not found")
            continue
        
        pcap_files = list(dataset['raw_dir'].glob("*.pcap"))
        
        if not pcap_files:
            print(f"  ⚠️ No PCAP files found")
            continue
        
        dataset_windows = 0
        complete = 0
        
        for pcap in sorted(pcap_files):
            size_mb = pcap.stat().st_size / (1024 * 1024)
            output_file = dataset['processed_dir'] / f"{pcap.stem}_features.json"
            
            if output_file.exists():
                try:
                    with open(output_file, 'r') as f:
                        data = json.load(f)
                    windows = len(data) if isinstance(data, list) else 1
                    status = f"✓ {windows} windows"
                    dataset_windows += windows
                    complete += 1
                except:
                    status = "⚠️ Corrupted"
            else:
                status = "⏳ Processing..."
            
            print(f"  {pcap.name:<35} {size_mb:>8.1f} MB  {status}")
        
        print(f"  {'-'*78}")
        print(f"  Status: {complete}/{len(pcap_files)} complete | {dataset_windows} windows extracted")
        grand_total_windows += dataset_windows
    
    print("\n" + "="*80)
    print(f"GRAND TOTAL: {grand_total_windows} windows extracted across all datasets")
    print("="*80 + "\n")
    
    return grand_total_windows

if __name__ == "__main__":
    total = check_all_progress()
    
    if total > 7000:
        print("🎉 Great! You have enough data for robust training.")
        print("   Run: python scripts\\train_model_combined.py")
    elif total > 2000:
        print("✅ Good progress! Continue extraction for more data.")
    else:
        print("⏳ Extraction in progress...")
