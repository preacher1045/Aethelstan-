"""
Batch extract features from multiple PCAP files using Rust extractor.
Processes all files in a directory and saves features separately.
"""

import subprocess
import json
from pathlib import Path
import sys

def extract_features(pcap_path: Path, output_dir: Path, rust_binary: Path):
    """Extract features from single PCAP file."""
    print(f"\n{'='*80}")
    print(f"Processing: {pcap_path.name}")
    print(f"Size: {pcap_path.stat().st_size / (1024*1024):.2f} MB")
    print(f"{'='*80}")
    
    # Output file name
    output_file = output_dir / f"{pcap_path.stem}_features.json"
    
    # Run Rust extractor
    cmd = [
        str(rust_binary),
        str(pcap_path),
        str(output_file)
    ]
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        if result.returncode == 0:
            # Check if output file exists
            if output_file.exists():
                with open(output_file, 'r') as f:
                    features = json.load(f)
                
                window_count = len(features) if isinstance(features, list) else 1
                print(f"✓ SUCCESS: Extracted {window_count} windows")
                print(f"  Output: {output_file}")
                return True, window_count
            else:
                print(f"✗ FAILED: Output file not created")
                print(f"  Stderr: {result.stderr}")
                return False, 0
        else:
            print(f"✗ FAILED: Return code {result.returncode}")
            print(f"  Stderr: {result.stderr}")
            return False, 0
            
    except subprocess.TimeoutExpired:
        print(f"✗ FAILED: Timeout after 10 minutes")
        return False, 0
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False, 0


def main():
    # Paths
    base_dir = Path(__file__).parent.parent
    rust_binary = base_dir / "backend" / "features" / "rust_extractor" / "target" / "release" / "rust_extractor.exe"
    
    # Define input/output directory pairs
    dataset_configs = [
        {
            'name': 'Local Captures',
            'input_dirs': [
                base_dir / "data" / "raw" / "local_captures_converted",
                base_dir / "data" / "raw" / "local_captures",
            ],
            'output_dir': base_dir / "data" / "processed" / "local_captures"
        },
        {
            'name': 'Enterprise PCAPs',
            'input_dirs': [
                base_dir / "data" / "raw" / "enterprise_pcap_files",
            ],
            'output_dir': base_dir / "data" / "processed" / "enterprise_pcap_files"
        }
    ]
    
    # Find all PCAP files from all datasets
    pcap_files = []
    output_mapping = {}
    
    for config in dataset_configs:
        config['output_dir'].mkdir(parents=True, exist_ok=True)
        
        for input_dir in config['input_dirs']:
            if input_dir.exists():
                for pcap in input_dir.glob("*.pcap"):
                    pcap_files.append(pcap)
                    # Map each pcap to its output directory
                    output_mapping[pcap] = config['output_dir']
    
    if not pcap_files:
        print(f"No .pcap files found in checked directories")
        print("If you have .pcapng files, run: python scripts\\convert_pcapng_to_pcap.py")
        sys.exit(1)
    
    print(f"\nFound {len(pcap_files)} PCAP files to process")
    
    # Check if Rust binary exists
    if not rust_binary.exists():
        print(f"\n✗ Rust extractor not found at: {rust_binary}")
        print("Building Rust extractor...")
        
        rust_dir = base_dir / "backend" / "features" / "rust_extractor"
        build_cmd = ["cargo", "build", "--release"]
        
        try:
            subprocess.run(build_cmd, cwd=rust_dir, check=True)
            print("✓ Rust extractor built successfully")
        except Exception as e:
            print(f"✗ Failed to build Rust extractor: {e}")
            sys.exit(1)
    
    # Process each file
    results = []
    total_windows = 0
    
    for pcap_file in pcap_files:
        output_dir = output_mapping[pcap_file]
        success, window_count = extract_features(pcap_file, output_dir, rust_binary)
        results.append({
            'file': pcap_file.name,
            'success': success,
            'windows': window_count
        })
        total_windows += window_count
    
    # Summary
    print(f"\n{'='*80}")
    print("BATCH EXTRACTION SUMMARY")
    print(f"{'='*80}")
    
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    
    print(f"Total files: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Total windows extracted: {total_windows}")
    
    print("\nDetails:")
    for r in results:
        status = "✓" if r['success'] else "✗"
        print(f"  {status} {r['file']}: {r['windows']} windows")
    
    # Save summary to first output directory used
    first_output_dir = list(set(output_mapping.values()))[0]
    summary_file = first_output_dir / "extraction_summary.json"
    with open(summary_file, 'w') as f:
        json.dump({
            'total_files': len(results),
            'successful': successful,
            'failed': failed,
            'total_windows': total_windows,
            'results': results
        }, f, indent=2)
    
    print(f"\n✓ Summary saved to: {summary_file}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
