"""Check extraction progress for local captures."""
import json
from pathlib import Path
from datetime import datetime

def check_progress():
    base_dir = Path(__file__).parent.parent
    raw_dir = base_dir / "data" / "raw" / "local_captures"
    processed_dir = base_dir / "data" / "processed" / "local_captures"
    
    print("\n" + "="*80)
    print(f"EXTRACTION PROGRESS CHECK - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    
    # Get all PCAP files
    pcap_files = list(raw_dir.glob("*.pcapng"))
    
    print(f"Source directory: {raw_dir}")
    print(f"Output directory: {processed_dir}")
    print(f"\nTotal PCAP files: {len(pcap_files)}\n")
    
    results = []
    total_windows = 0
    
    for pcap in sorted(pcap_files):
        size_mb = pcap.stat().st_size / (1024 * 1024)
        output_file = processed_dir / f"{pcap.stem}_features.json"
        
        if output_file.exists():
            try:
                with open(output_file, 'r') as f:
                    data = json.load(f)
                windows = len(data) if isinstance(data, list) else 1
                status = f"✓ Complete ({windows} windows)"
                total_windows += windows
            except:
                status = "⚠️ Incomplete/Corrupted"
                windows = 0
        else:
            status = "⏳ Pending"
            windows = 0
        
        results.append({
            'file': pcap.name,
            'size_mb': size_mb,
            'status': status,
            'windows': windows
        })
    
    # Print table
    print(f"{'File':<35} {'Size (MB)':>12} {'Windows':>10}  {'Status':<25}")
    print("-" * 80)
    
    for r in results:
        print(f"{r['file']:<35} {r['size_mb']:>12.1f} {r['windows']:>10}  {r['status']:<25}")
    
    print("-" * 80)
    print(f"{'TOTAL':<35} {sum(r['size_mb'] for r in results):>12.1f} {total_windows:>10}")
    print("=" * 80)
    
    # Summary
    complete = sum(1 for r in results if '✓' in r['status'])
    pending = sum(1 for r in results if '⏳' in r['status'])
    
    print(f"\nStatus: {complete}/{len(results)} complete | {pending} pending")
    
    if complete == len(results):
        print("\n🎉 All extractions complete!")
        print(f"\nNext step: python scripts\\train_on_local_captures.py")
    elif complete > 0:
        print(f"\n⏳ Extraction in progress... ({complete}/{len(results)} done)")
        print("   Check back later or wait for current extraction to finish")
    else:
        print("\n⚠️ No extractions completed yet")
        print("   Run: python scripts\\batch_extract_features.py")
    
    print("=" * 80 + "\n")
    
    return complete == len(results)

if __name__ == "__main__":
    check_progress()
