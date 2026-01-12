import pandas as pd
import numpy as np

print("="*60)
print("ANALYZING UNCAPPED MASTERLIST")
print("Finding rugs with empty pattern")
print("="*60)

# Process CSV file in chunks for better memory efficiency
print("\nProcessing CSV file in chunks...")
chunk_size = 10000
results = []
variant_skus_set = set()
total_rows = 0
rugs_count = 0

for chunk_num, chunk in enumerate(pd.read_csv('../data/uncapped_masterlist-260106_0814.csv', chunksize=chunk_size, low_memory=False), 1):
    total_rows += len(chunk)
    
    # Clean column names
    chunk.columns = chunk.columns.str.strip()
    
    # Filter for rugs where Type contains "rug" (case-insensitive) - catches "Rugs", "Rug Accessories", "Custom Size Rugs"
    type_lower = chunk['Type'].astype(str).str.strip().str.lower()
    rugs_chunk = chunk[type_lower.str.contains('rug', na=False)].copy()
    rugs_count += len(rugs_chunk)
    
    if len(rugs_chunk) > 0:
        # Find rugs with empty pattern
        empty_pattern_mask = (
            rugs_chunk['Patterns'].isna() | 
            (rugs_chunk['Patterns'].astype(str).str.strip() == '') |
            (rugs_chunk['Patterns'].astype(str).str.strip().str.lower() == 'nan')
        )
        
        rugs_empty_pattern_chunk = rugs_chunk[empty_pattern_mask].copy()
        
        if len(rugs_empty_pattern_chunk) > 0:
            results.append(rugs_empty_pattern_chunk)
            # Add variant_skus to set
            variant_skus_set.update(rugs_empty_pattern_chunk['Variant SKU'].dropna().astype(str))
    
    if chunk_num % 10 == 0:
        print(f"  Processed {total_rows:,} rows... Found {rugs_count:,} rugs so far...")

print(f"\nProcessing complete!")
print(f"Total rows processed: {total_rows:,}")
print(f"Total rugs found: {rugs_count:,}")

# Combine all results
if results:
    rugs_empty_pattern = pd.concat(results, ignore_index=True)
    print(f"Rugs with empty pattern: {len(rugs_empty_pattern):,}")
    print(f"Unique variant_sku values: {len(variant_skus_set):,}")
    
    # Create output file with results
    output_file = "../data/rugs_empty_pattern_results.csv"
    rugs_empty_pattern.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\nSaved full results to: {output_file}")
    
    # Create a simple list of variant_skus
    variant_sku_file = "rugs_empty_pattern_variant_skus.txt"
    with open(variant_sku_file, 'w', encoding='utf-8') as f:
        for sku in sorted(variant_skus_set):
            f.write(f"{sku}\n")
    
    print(f"Saved variant_sku list to: {variant_sku_file}")
    
    # Display summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total rows in masterlist: {total_rows:,}")
    print(f"Total rugs found: {rugs_count:,}")
    print(f"Rugs with empty pattern: {len(rugs_empty_pattern):,}")
    print(f"Unique variant_sku values: {len(variant_skus_set):,}")
    
    # Display first 20 variant_skus
    if len(variant_skus_set) > 0:
        print("\n" + "="*60)
        print("FIRST 20 VARIANT_SKUs (sorted)")
        print("="*60)
        sorted_skus = sorted(variant_skus_set)
        for i, sku in enumerate(sorted_skus[:20], 1):
            print(f"{i}. {sku}")
        
        if len(variant_skus_set) > 20:
            print(f"\n... and {len(variant_skus_set) - 20:,} more (see {variant_sku_file} for full list)")
    
    # Display sample rows
    print("\n" + "="*60)
    print("SAMPLE ROWS (first 10)")
    print("="*60)
    display_cols = ['Variant SKU', 'Product SKU', 'Type', 'Patterns', 'Collection Group', 'Brand']
    available_cols = [col for col in display_cols if col in rugs_empty_pattern.columns]
    print(rugs_empty_pattern[available_cols].head(10).to_string(index=False))
else:
    print("\nNo rugs found with empty pattern.")

print("\n" + "="*60)
print("ANALYSIS COMPLETE")
print("="*60)
