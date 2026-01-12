import pandas as pd

print("="*60)
print("STEP-BY-STEP DEBUGGING")
print("="*60)

# Step 1: Check column names
print("\nSTEP 1: Checking column names...")
df_sample = pd.read_csv('uncapped_masterlist-260106_0814.csv', nrows=5)
print("Column names:")
for i, col in enumerate(df_sample.columns, 1):
    print(f"  {i}. '{col}'")

# Step 2: Check Type column values
print("\n" + "="*60)
print("STEP 2: Checking Type column values...")
df_type = pd.read_csv('uncapped_masterlist-260106_0814.csv', usecols=['Type'])
print(f"Total rows: {len(df_type):,}")
print("\nType value counts (top 20):")
print(df_type['Type'].value_counts().head(20))
print("\nChecking for 'rug' variations...")
type_lower = df_type['Type'].astype(str).str.strip().str.lower()
print(f"Rows with 'rug' (lowercase): {len(type_lower[type_lower == 'rug']):,}")
print(f"Rows containing 'rug': {len(type_lower[type_lower.str.contains('rug', na=False)]):,}")

# Step 3: Check Patterns column
print("\n" + "="*60)
print("STEP 3: Checking Patterns column...")
df_patterns = pd.read_csv('uncapped_masterlist-260106_0814.csv', usecols=['Patterns'])
print(f"Total rows: {len(df_patterns):,}")
print(f"Null/NaN values: {df_patterns['Patterns'].isna().sum():,}")
print(f"Empty strings: {(df_patterns['Patterns'].astype(str).str.strip() == '').sum():,}")
print(f"Non-empty values: {len(df_patterns) - df_patterns['Patterns'].isna().sum() - (df_patterns['Patterns'].astype(str).str.strip() == '').sum():,}")

# Step 4: Filter for rugs
print("\n" + "="*60)
print("STEP 4: Filtering for rugs...")
df = pd.read_csv('uncapped_masterlist-260106_0814.csv', low_memory=False)
print(f"Total rows loaded: {len(df):,}")

# Check Type column
type_col = 'Type'
print(f"\nType column values (case-insensitive check):")
type_lower = df[type_col].astype(str).str.strip().str.lower()
print(f"  'rug': {len(type_lower[type_lower == 'rug']):,}")
print(f"  'rugs': {len(type_lower[type_lower == 'rugs']):,}")
print(f"  contains 'rug': {len(type_lower[type_lower.str.contains('rug', na=False)]):,}")

# Show unique type values that contain 'rug'
rug_types = df[type_lower.str.contains('rug', na=False)][type_col].unique()
print(f"\nUnique Type values containing 'rug': {list(rug_types)}")

# Step 5: Filter rugs and check patterns
print("\n" + "="*60)
print("STEP 5: Filtering rugs and checking patterns...")
rugs_df = df[type_lower.str.contains('rug', na=False)].copy()
print(f"Rugs found: {len(rugs_df):,}")

if len(rugs_df) > 0:
    # Check patterns
    patterns_col = 'Patterns'
    empty_pattern_mask = (
        rugs_df[patterns_col].isna() | 
        (rugs_df[patterns_col].astype(str).str.strip() == '') |
        (rugs_df[patterns_col].astype(str).str.strip().str.lower() == 'nan')
    )
    
    rugs_empty_pattern = rugs_df[empty_pattern_mask].copy()
    print(f"Rugs with empty pattern: {len(rugs_empty_pattern):,}")
    
    if len(rugs_empty_pattern) > 0:
        variant_skus = rugs_empty_pattern['Variant SKU'].dropna().unique()
        print(f"Unique variant_sku values: {len(variant_skus):,}")
        
        print("\nFirst 10 variant_skus:")
        for i, sku in enumerate(variant_skus[:10], 1):
            print(f"  {i}. {sku}")

print("\n" + "="*60)
print("DEBUGGING COMPLETE")
print("="*60)

