import pandas as pd
import json
import ast

print("="*60)
print("EXTRACTING RUGS WITH DESIGN IMAGES")
print("="*60)

# Read the rugs with empty pattern results
print("\nReading rugs with empty pattern...")
rugs_df = pd.read_csv('../data/rugs_empty_pattern_results.csv', low_memory=False)

print(f"Total rugs with empty pattern: {len(rugs_df):,}")

# Function to extract design image URL from Images column
def extract_design_image(images_str):
    """Extract the image URL where angle is 'design'"""
    if pd.isna(images_str) or images_str == '':
        return None
    
    try:
        # Parse as JSON string
        if isinstance(images_str, str):
            images_list = json.loads(images_str)
            
            # If it's a list, iterate through to find angle == "design"
            if isinstance(images_list, list):
                for img in images_list:
                    if isinstance(img, dict):
                        # Check if angle is "design"
                        angle = img.get('angle', '')
                        if angle and angle.lower() == 'design':
                            return img.get('url', '')
            
            # If it's a dict, check directly
            elif isinstance(images_list, dict):
                angle = images_list.get('angle', '')
                if angle and angle.lower() == 'design':
                    return images_list.get('url', '')
        
        return None
    except Exception as e:
        return None

# Extract design images
print("\nExtracting design image URLs from Images column...")
print("This may take a moment for large datasets...")

# Process in batches with progress updates
batch_size = 5000
total_batches = (len(rugs_df) + batch_size - 1) // batch_size
design_image_urls = []

for i in range(0, len(rugs_df), batch_size):
    batch = rugs_df.iloc[i:i+batch_size]
    batch_urls = batch['Images'].apply(extract_design_image)
    design_image_urls.extend(batch_urls)
    
    if (i // batch_size + 1) % 5 == 0:
        print(f"  Processed {min(i+batch_size, len(rugs_df)):,} / {len(rugs_df):,} rows...")

rugs_df['Design Image URL'] = design_image_urls

# Count how many have design images
design_image_count = rugs_df['Design Image URL'].notna().sum()
print(f"Rugs with design images found: {design_image_count:,}")
print(f"Rugs without design images: {len(rugs_df) - design_image_count:,}")

# Create output with required columns
print("\n" + "="*60)
print("CREATING OUTPUT FILE")
print("="*60)

output_df = rugs_df[['Variant SKU', 'Product SKU', 'Patterns', 'Design Image URL']].copy()

# Save to CSV
output_file = "../data/rugs_empty_pattern_with_design_images.csv"
output_df.to_csv(output_file, index=False, encoding='utf-8-sig')
print(f"\nSaved results to: {output_file}")

# Display summary
print("\n" + "="*60)
print("SUMMARY")
print("="*60)
print(f"Total rows: {len(output_df):,}")
print(f"Rows with design images: {design_image_count:,}")
print(f"Rows without design images: {len(output_df) - design_image_count:,}")

# Display first 10 rows
print("\n" + "="*60)
print("FIRST 10 ROWS")
print("="*60)
print(output_df.head(10).to_string(index=False))

print("\n" + "="*60)
print("EXTRACTION COMPLETE")
print("="*60)

