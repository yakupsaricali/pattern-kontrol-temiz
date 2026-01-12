import pandas as pd
import requests
import os
from google import genai
from google.genai import types
import time

print("="*60)
print("FAST AI PATTERN EXTRACTION TEST")
print("="*60)

# Configuration
TEST_SAMPLE_SIZE = 5  # Process 5 images for quick test
# API Key - Environment variable kullan (güvenlik için)
import os
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set!")
MODEL_NAME = "models/gemini-1.5-flash"  # Daha yüksek günlük limit (1500/gün)

# Initialize client
print("\nInitializing Gemini client...")
client = genai.Client(api_key=API_KEY)

# Read CSV
print("Reading CSV file...")
df = pd.read_csv('rugs_empty_pattern_with_design_images.csv')
df_with_images = df[df['Design Image URL'].notna() & (df['Design Image URL'] != '')].copy()
print(f"Found {len(df_with_images):,} rows with images")

# Get unique URLs
df_unique = df_with_images.drop_duplicates(subset=['Design Image URL'], keep='first')

# Skip already tested
tested_urls = set()
if os.path.exists('test_ai_pattern_results.csv'):
    try:
        prev = pd.read_csv('test_ai_pattern_results.csv')
        if 'Design Image URL' in prev.columns:
            tested_urls = set(prev['Design Image URL'].dropna())
            print(f"Skipping {len(tested_urls)} already tested URLs")
    except:
        pass

df_new = df_unique[~df_unique['Design Image URL'].isin(tested_urls)].copy()
test_sample = df_new.head(TEST_SAMPLE_SIZE).copy()
print(f"\nProcessing {len(test_sample)} NEW images\n")

# Prompt
prompt = """Analyze this rug image and identify ONLY the VISUAL PATTERN (not style).

PATTERNS: Geometric, Floral, Striped, Solid, Abstract, Medallion, Tribal, Chevron, Paisley, Damask, Ikat, Herringbone, Plaid, Polka Dot, Animal Print

NOT STYLES: Oriental, Persian, Moroccan, Turkish, Traditional, Modern, Contemporary, Boho

Return ONLY the pattern name. If unknown, return 'Unknown'.

Pattern:"""

results = []
start_total = time.time()

for i, (idx, row) in enumerate(test_sample.iterrows(), 1):
    variant_sku = row['Variant SKU']
    image_url = row['Design Image URL']
    
    print(f"[{i}/{len(test_sample)}] {variant_sku}")
    print(f"  URL: {image_url[:70]}...")
    
    start = time.time()
    pattern = None
    
    try:
        # Download image
        img_resp = requests.get(image_url, timeout=5)
        img_resp.raise_for_status()
        
        # Get content type
        content_type = img_resp.headers.get('content-type', 'image/jpeg')
        if 'image' not in content_type:
            content_type = 'image/jpeg'
        
        # Create image part
        image_part = types.Part.from_bytes(
            data=img_resp.content,
            mime_type=content_type
        )
        
        # API call
        print("  Calling Gemini API...")
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt, image_part]
        )
        
        pattern = response.text.strip()
        elapsed = time.time() - start
        print(f"  [OK] Pattern: {pattern} ({elapsed:.1f}s)")
        
    except Exception as e:
        elapsed = time.time() - start
        error_msg = str(e)[:150]
        
        # Check for quota limit
        if "429" in error_msg or "quota" in error_msg.lower():
            print(f"  [QUOTA LIMIT] Daily limit reached. Need to wait or upgrade plan.")
            print(f"  Error details: {error_msg}")
            pattern = 'QuotaExceeded'
        else:
            print(f"  [ERROR] {error_msg} ({elapsed:.1f}s)")
            pattern = 'Error'
    
    results.append({
        'Variant SKU': variant_sku,
        'Product SKU': row['Product SKU'],
        'Original Patterns': row['Patterns'],
        'AI Detected Pattern': pattern,
        'Design Image URL': image_url
    })
    
    # Wait between requests (15 requests/min = 4 seconds between requests)
    if i < len(test_sample):
        print(f"  Waiting 4s...\n")
        time.sleep(4)

# Save results
results_df = pd.DataFrame(results)
output_file = "test_ai_pattern_results.csv"

if os.path.exists(output_file):
    results_df.to_csv(output_file, mode='a', header=False, index=False, encoding='utf-8-sig')
    print(f"✓ Appended {len(results_df)} results to {output_file}")
else:
    results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"✓ Saved {len(results_df)} results to {output_file}")

total_time = time.time() - start_total
print(f"\n{'='*60}")
print(f"COMPLETE - Total time: {total_time/60:.1f} minutes")
print(f"{'='*60}")
print("\nResults:")
print(results_df[['Variant SKU', 'AI Detected Pattern']].to_string(index=False))
print(f"\nPattern distribution:")
print(results_df['AI Detected Pattern'].value_counts())

