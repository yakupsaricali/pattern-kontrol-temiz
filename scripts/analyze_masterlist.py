import pandas as pd
import requests
from io import StringIO
import os

# Google Sheets export URL
SHEET_ID = "1JvxWUtkgY_yCuK8jUBe4YQKX99kEvM9Y0KtDUh5if6I"
GID = "0"

def fetch_google_sheets_data():
    """Try different methods to fetch Google Sheets data"""
    # Method 1: Standard CSV export
    csv_urls = [
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}",
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&gid={GID}",
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv",
    ]
    
    for url in csv_urls:
        try:
            print(f"Trying to fetch from: {url[:80]}...")
            response = requests.get(url, timeout=15)
            if response.status_code == 200 and len(response.text) > 100:
                print("Successfully fetched data!")
                return response.text
        except Exception as e:
            print(f"  Failed: {str(e)[:50]}")
            continue
    
    return None

print("="*60)
print("ANALYZING MASTERLIST - FINDING RUGS WITH BLANK COLLECTION GROUP")
print("="*60)

# Check if CSV already exists locally (try multiple possible filenames)
csv_path = None
possible_paths = [
    "../masterist/masterlist.csv",
    "../data/Metadata Masterlist 2026 - Sheet1.csv",
    "masterlist.csv"
]

for path in possible_paths:
    if os.path.exists(path):
        csv_path = path
        print(f"\nFound CSV file: {csv_path}")
        break

if csv_path:
    csv_data = open(csv_path, 'r', encoding='utf-8').read()
else:
    print("\nFetching data from Google Sheets...")
    csv_data = fetch_google_sheets_data()
    
    if csv_data is None:
        print("\nERROR: Could not fetch data from Google Sheets.")
        print("The sheet may require authentication or may not be publicly accessible.")
        print("\nPlease do one of the following:")
        print("1. Make the Google Sheet publicly viewable, OR")
        print("2. Export the sheet as CSV manually")
        print("3. Save it as 'masterist/masterlist.csv'")
        print("4. Run this script again")
        exit(1)
    
    # Save the fetched data
    os.makedirs("masterist", exist_ok=True)
    with open(csv_path, 'w', encoding='utf-8') as f:
        f.write(csv_data)
    print(f"Saved masterlist to {csv_path}")

# Read CSV data
print("\nReading CSV data...")
df = pd.read_csv(StringIO(csv_data))

print(f"Loaded {len(df)} rows")
print(f"Found {len(df.columns)} columns")

# Clean column names
df.columns = df.columns.str.strip()

print("\nColumn names:")
for i, col in enumerate(df.columns, 1):
    print(f"  {i}. {col}")

# Display first few rows
print("\nFirst 3 rows preview:")
print(df.head(3).to_string())

# Find columns related to type and collection group
print("\n" + "="*60)
print("IDENTIFYING RELEVANT COLUMNS")
print("="*60)

# Find type column (for filtering rugs where type == "Rugs")
type_col = None
for col in df.columns:
    col_lower = col.lower()
    if col_lower == 'type' or 'type' in col_lower:
        type_col = col
        break

# If not found, try alternative names
if not type_col:
    for col in df.columns:
        col_lower = col.lower()
        if any(kw in col_lower for kw in ['product type', 'category', 'product_category']):
            type_col = col
            break

# Find collection group column
collection_col = None
collection_keywords = ['collection', 'group']
for col in df.columns:
    col_lower = col.lower()
    # Check for exact match or contains both keywords
    if col_lower == 'collection group' or (col_lower == 'collectiongroup') or \
       ('collection' in col_lower and 'group' in col_lower):
        collection_col = col
        break
    elif any(kw in col_lower for kw in collection_keywords):
        collection_col = col
        break

print(f"\nType column identified: {type_col}")
print(f"Collection group column identified: {collection_col}")

if not type_col:
    print("\nWARNING: Could not find 'type' column automatically.")
    print("Please check the column names above and update the script if needed.")
    exit(1)

if not collection_col:
    print("\nWARNING: Could not find 'collection group' column automatically.")
    print("Please check the column names above and update the script if needed.")
    exit(1)

# Filter for rugs (where type == "Rugs")
print("\n" + "="*60)
print("FILTERING FOR RUGS (Type = 'Rugs')")
print("="*60)

# Filter for products where type is "Rugs"
rugs_df = df[df[type_col].astype(str).str.strip().str.lower() == 'rugs'].copy()

print(f"Found {len(rugs_df)} rugs")

if len(rugs_df) == 0:
    print("\nWARNING: No rugs found in the dataset.")
    print("Please verify the data or column names.")
    exit(1)

# Find rugs with blank collection group
print("\n" + "="*60)
print("FINDING RUGS WITH BLANK COLLECTION GROUP")
print("="*60)

# Check for blank values (NaN, empty string, whitespace only)
blank_mask = (
    rugs_df[collection_col].isna() | 
    (rugs_df[collection_col].astype(str).str.strip() == '') |
    (rugs_df[collection_col].astype(str).str.strip().str.lower() == 'nan')
)

rugs_with_blank_collection = rugs_df[blank_mask].copy()

print(f"Found {len(rugs_with_blank_collection)} rugs with blank collection group")

# Create output file
output_file = "../masterist/rugs_blank_collection_group.csv"
rugs_with_blank_collection.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"\nSaved results to: {output_file}")

# Display results
if len(rugs_with_blank_collection) > 0:
    print("\n" + "="*60)
    print("RESULTS - RUGS WITH BLANK COLLECTION GROUP")
    print("="*60)
    
    # Select relevant columns to display
    display_cols = []
    priority_cols = ['sku', 'id', 'name', 'product', 'title', type_col, collection_col]
    
    for col in priority_cols:
        if col and col in rugs_with_blank_collection.columns:
            display_cols.append(col)
    
    # Add collection_col if not already included
    if collection_col not in display_cols:
        display_cols.append(collection_col)
    
    # Limit to first 10 columns to avoid clutter
    display_cols = display_cols[:10]
    
    print(f"\nShowing {len(rugs_with_blank_collection)} rows:")
    print(rugs_with_blank_collection[display_cols].to_string(index=False))
    
    print(f"\nTotal rugs with blank collection group: {len(rugs_with_blank_collection)}")
    print(f"Full results saved to: {output_file}")
else:
    print("\nNo rugs found with blank collection group. All rugs have collection group values.")

print("\n" + "="*60)
print("ANALYSIS COMPLETE")
print("="*60)

