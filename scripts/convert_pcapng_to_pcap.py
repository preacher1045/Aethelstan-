"""
Convert PCAPNG files to standard PCAP format.
Required because Rust pcap crate doesn't support pcapng natively.
"""

from pathlib import Path
import sys

try:
    from scapy.all import rdpcap, wrpcap
    print("✓ Scapy available")
except ImportError:
    print("❌ Scapy not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "scapy"])
    from scapy.all import rdpcap, wrpcap
    print("✓ Scapy installed successfully")

def convert_pcapng_to_pcap(pcapng_file: Path, pcap_file: Path) -> bool:
    """Convert .pcapng to .pcap format."""
    try:
        print(f"Converting: {pcapng_file.name}")
        print(f"  Reading packets...")
        
        # Read pcapng
        packets = rdpcap(str(pcapng_file))
        print(f"  ✓ Read {len(packets)} packets")
        
        # Write as pcap
        wrpcap(str(pcap_file), packets)
        print(f"  ✓ Saved to: {pcap_file.name}")
        
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False

def main():
    base_dir = Path(__file__).parent.parent
    input_dir = base_dir / "data" / "raw" / "local_captures"
    output_dir = base_dir / "data" / "raw" / "local_captures_converted"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*80)
    print("PCAPNG TO PCAP CONVERTER")
    print("="*80 + "\n")
    
    # Find all pcapng files
    pcapng_files = list(input_dir.glob("*.pcapng"))
    
    if not pcapng_files:
        print(f"No .pcapng files found in {input_dir}")
        return
    
    print(f"Found {len(pcapng_files)} files to convert\n")
    
    results = []
    for pcapng_file in sorted(pcapng_files):
        pcap_file = output_dir / pcapng_file.name.replace('.pcapng', '.pcap')
        
        success = convert_pcapng_to_pcap(pcapng_file, pcap_file)
        results.append({'file': pcapng_file.name, 'success': success})
        print()
    
    # Summary
    print("="*80)
    print("CONVERSION SUMMARY")
    print("="*80)
    
    successful = sum(1 for r in results if r['success'])
    print(f"Total files: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(results) - successful}")
    print(f"\nConverted files saved to: {output_dir}")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
