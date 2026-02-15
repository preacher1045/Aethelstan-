"""
Combine multiple feature files into a unified training dataset.
Tracks source file for each window and prepares for model training.
"""

import json
import pandas as pd
from pathlib import Path
from typing import List, Dict
import sys

def load_feature_file(file_path: Path) -> pd.DataFrame:
    """Load features from JSON file."""
    print(f"Loading: {file_path.name}")
    
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    if isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = pd.DataFrame([data])
    
    # Add source file metadata
    df['source_file'] = file_path.stem.replace('_features', '')
    
    print(f"  ✓ {len(df)} windows loaded")
    return df

def combine_datasets(
    feature_dir: Path,
    output_file: Path,
    dataset_name: str = "local_captures"
) -> pd.DataFrame:
    """Combine all feature files in directory."""
    
    print(f"\n{'='*80}")
    print(f"COMBINING DATASETS: {dataset_name}")
    print(f"{'='*80}\n")
    
    # Find all feature JSON files
    feature_files = list(feature_dir.glob("*_features.json"))
    
    if not feature_files:
        print(f"No feature files found in {feature_dir}")
        sys.exit(1)
    
    print(f"Found {len(feature_files)} feature files\n")
    
    # Load and combine
    all_dfs = []
    for file_path in sorted(feature_files):
        df = load_feature_file(file_path)
        all_dfs.append(df)
    
    # Combine
    combined_df = pd.concat(all_dfs, ignore_index=True)
    
    print(f"\n{'='*80}")
    print("COMBINATION SUMMARY")
    print(f"{'='*80}")
    print(f"Total windows: {len(combined_df)}")
    print(f"Total features: {len(combined_df.columns) - 1}")  # -1 for source_file
    print(f"\nWindows per source:")
    for source in combined_df['source_file'].unique():
        count = (combined_df['source_file'] == source).sum()
        pct = 100 * count / len(combined_df)
        print(f"  {source}: {count} ({pct:.1f}%)")
    
    # Save combined dataset
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Save as JSON
    combined_df.to_json(output_file, orient='records', indent=2)
    print(f"\n✓ Combined dataset saved to: {output_file}")
    
    # Also save as CSV for easy inspection
    csv_file = output_file.with_suffix('.csv')
    combined_df.to_csv(csv_file, index=False)
    print(f"✓ CSV version saved to: {csv_file}")
    
    # Save metadata
    metadata = {
        'dataset_name': dataset_name,
        'total_windows': len(combined_df),
        'total_features': len(combined_df.columns) - 1,
        'source_files': [
            {
                'name': source,
                'windows': int((combined_df['source_file'] == source).sum())
            }
            for source in combined_df['source_file'].unique()
        ],
        'feature_names': [col for col in combined_df.columns if col != 'source_file']
    }
    
    metadata_file = output_file.parent / f"{output_file.stem}_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"✓ Metadata saved to: {metadata_file}")
    
    print(f"{'='*80}\n")
    
    return combined_df

def main():
    base_dir = Path(__file__).parent.parent
    
    # Local captures
    local_features_dir = base_dir / "data" / "processed" / "local_captures"
    local_output = base_dir / "data" / "training" / "local_captures_combined.json"
    
    if local_features_dir.exists():
        print("Processing LOCAL CAPTURES...")
        df_local = combine_datasets(
            local_features_dir,
            local_output,
            "local_captures"
        )
        print(f"Local captures: {len(df_local)} total windows\n")
    else:
        print(f"Local captures directory not found: {local_features_dir}\n")
    
    # Note for future enterprise datasets
    print("=" * 80)
    print("NOTE: To add enterprise captures later:")
    print("1. Extract features: python scripts/batch_extract_features.py")
    print("2. Run this script again to combine all datasets")
    print("3. Use data/training/*_combined.json for model training")
    print("=" * 80)

if __name__ == "__main__":
    main()
