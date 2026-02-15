"""
Consolidate all available training data from multiple sources.
This gives us a much larger, more diverse training set for scale-robust model.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

def consolidate_training_data():
    """Load and merge all available training feature files."""
    
    data_dir = ROOT / 'data' / 'processed'
    
    # Check all potential training data sources
    sources = [
        '2023_test_features.json',
        'test_net_traffic_features.json',
        'window_features.json',
    ]
    
    consolidated = []
    total_windows = 0
    
    print("Consolidating training data...")
    print("-" * 60)
    
    for source in sources:
        path = data_dir / source
        if path.exists():
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                
                if isinstance(data, list):
                    consolidated.extend(data)
                    num_windows = len(data)
                else:
                    # Single record
                    consolidated.append(data)
                    num_windows = 1
                
                total_windows += num_windows
                print(f"✓ {source}: {num_windows} windows")
            except Exception as e:
                print(f"✗ {source}: {e}")
        else:
            print(f"- {source}: Not found")
    
    print("-" * 60)
    print(f"Total: {total_windows} windows consolidated\n")
    
    # Save consolidated data
    out_path = data_dir / 'training_data_consolidated.json'
    with open(out_path, 'w') as f:
        json.dump(consolidated, f)
    
    print(f"✓ Consolidated training data saved: {out_path.name}")
    return out_path, total_windows

if __name__ == '__main__':
    consolidate_training_data()
