import pandas as pd
import requests
import os
from google import genai
from google.genai import types
import time

print("="*60)
print("AI PATTERN EXTRACTION - TEST SCRIPT (Google Gemini)")
print("="*60)

# Configuration
TEST_SAMPLE_SIZE = 20  # 20 ürün test et
API_KEY_ENV = "GEMINI_API_KEY"  # Environment variable name for API key
MODEL_NAME = "models/gemini-2.5-flash"  # Ücretsiz tier: 20 istek/gün (çalışan model)

# API Key - You can set it here directly for testing, or use environment variable
# API Key - Sadece environment variable kullan (güvenlik için)
DIRECT_API_KEY = None  # Set to None to use env var instead

# Check for API key
if DIRECT_API_KEY:
    api_key = DIRECT_API_KEY
    print(f"\nUsing API key from script configuration.")
else:
    api_key = os.getenv(API_KEY_ENV)
    if not api_key:
        print(f"\nWARNING: {API_KEY_ENV} environment variable not found.")
        print("Please set your Google Gemini API key:")
        print(f"  Windows: set {API_KEY_ENV}=your_api_key_here")
        print(f"  Linux/Mac: export {API_KEY_ENV}=your_api_key_here")
        print("\nAlternatively, you can enter it when prompted.")
        api_key = input("Enter your Gemini API key (or press Enter to skip): ").strip()
        if not api_key:
            print("Cannot proceed without API key. Exiting.")
            exit(1)

# Initialize Gemini client
client = genai.Client(api_key=api_key)

# Read the CSV file
print("\nReading CSV file...")
df = pd.read_csv('../data/rugs_empty_pattern_with_design_images_removedsames.csv')

# Filter to rows with design image URLs
df_with_images = df[df['Design Image URL'].notna() & (df['Design Image URL'] != '')].copy()
print(f"Total rows with design images: {len(df_with_images):,}")

# Get unique image URLs (to avoid analyzing the same image multiple times)
unique_images = df_with_images['Design Image URL'].unique()
print(f"Unique image URLs: {len(unique_images):,}")

# Take a test sample with unique image URLs
# Get first occurrence of each unique URL
df_unique = df_with_images.drop_duplicates(subset=['Design Image URL'], keep='first')

# Check if we have previous test results to skip already tested URLs
tested_urls = set()
if os.path.exists('../data/test_ai_pattern_results.csv'):
    try:
        previous_results = pd.read_csv('../data/test_ai_pattern_results.csv')
        if 'Design Image URL' in previous_results.columns:
            tested_urls = set(previous_results['Design Image URL'].dropna())
            print(f"Found {len(tested_urls)} already tested URLs. Skipping them...")
    except:
        pass

# Filter out already tested URLs
df_new = df_unique[~df_unique['Design Image URL'].isin(tested_urls)].copy()
print(f"Available new unique URLs: {len(df_new):,}")

# Take a test sample with NEW unique image URLs
test_sample = df_new.head(TEST_SAMPLE_SIZE).copy()
print(f"\nTest sample size: {len(test_sample)} rows (all NEW unique image URLs)")

# Function to analyze image with AI (with retry logic)
def analyze_image_with_ai(image_url, max_retries=3):
    """Use Google Gemini API to analyze rug image and extract pattern"""
    for attempt in range(max_retries):
        try:
            # Download image from URL (reduced timeout)
            img_response = requests.get(image_url, timeout=5)
            img_response.raise_for_status()
            
            # Prepare prompt - Focus on PATTERNS, not styles
            prompt = """You are an expert in rug patterns and design. Analyze this rug image and identify the VISUAL PATTERN type.

IMPORTANT: Return ONLY the PATTERN name, NOT the style. Patterns describe the visual design elements (shapes, lines, motifs), while styles describe cultural or design movements.

PATTERNS (correct examples):
- Geometric (shapes, lines, angles)
- Floral (flowers, botanical elements)
- Striped (horizontal or vertical lines)
- Solid (no pattern, single color)
- Abstract (non-representational shapes)
- Medallion (central circular/oval design)
- Tribal (ethnic motifs, symbols)
- Chevron (zigzag pattern)
- Paisley (teardrop-shaped motifs)
- Damask (reversible figured fabric pattern)
- Ikat (tie-dye pattern)
- Herringbone (V-shaped pattern)
- Plaid/Checkered (grid pattern)
- Polka Dot (dots)
- Animal Print (zebra, leopard, etc.)

STYLES (DO NOT USE - these are styles, not patterns):
- Oriental, Persian, Moroccan, Turkish, Traditional, Modern, Contemporary, Boho, etc.

Return ONLY the pattern name. If you cannot determine the pattern, return 'Unknown'.

Pattern name:"""
            
            # Use Gemini to analyze the image
            # Get content type
            content_type = img_response.headers.get('content-type', 'image/jpeg')
            if 'image' not in content_type:
                # Fallback: check URL extension
                if image_url.lower().endswith('.png'):
                    content_type = 'image/png'
                elif image_url.lower().endswith('.jpg') or image_url.lower().endswith('.jpeg'):
                    content_type = 'image/jpeg'
                else:
                    content_type = 'image/jpeg'  # Default
            
            # Use the new google.genai API
            image_part = types.Part.from_bytes(
                data=img_response.content,
                mime_type=content_type
            )
            
            # Make API call (timeout handled by client)
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[prompt, image_part]
            )
            
            pattern = response.text.strip()
            return pattern
            
        except Exception as e:
            error_str = str(e)
            
            # Check if it's a rate limit/quota error
            if "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower():
                import re
                # Check if limit is 0 (model not available in free tier)
                if "limit: 0" in error_str or "limit:0" in error_str:
                    print(f"  [HATA] Bu model ucretsiz tier'da kullanilamiyor (limit: 0)")
                    print(f"  Lutfen farkli bir model kullanin (orn: gemini-2.5-flash)")
                    return None  # Don't retry, model not available
                
                retry_match = re.search(r'retry in (\d+)', error_str)
                if retry_match:
                    retry_seconds = int(retry_match.group(1))
                    if attempt < max_retries - 1:
                        print(f"  Rate limit hit. Waiting {retry_seconds + 5} seconds before retry {attempt + 2}/{max_retries}...")
                        time.sleep(retry_seconds + 5)  # Add buffer
                        continue
                else:
                    # Default wait time for rate limits (reduced)
                    wait_time = 30 * (attempt + 1)  # Exponential backoff: 30s, 60s, 90s (reduced from 60s, 120s, 180s)
                    if attempt < max_retries - 1:
                        print(f"  Rate limit hit. Waiting {wait_time} seconds before retry {attempt + 2}/{max_retries}...")
                        time.sleep(wait_time)
                        continue
            
            # For other errors, retry with shorter delay
            if attempt < max_retries - 1:
                wait_time = 3 * (attempt + 1)  # 3s, 6s, 9s (reduced from 5s, 10s, 15s)
                print(f"  Error (attempt {attempt + 1}/{max_retries}): {error_str[:100]}")
                print(f"  Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"  Error after {max_retries} attempts: {error_str[:200]}")
                return None
    
    return None

# Analyze images in test sample
print("\n" + "="*60)
print("ANALYZING IMAGES WITH AI")
print("="*60)

results = []
for i, (idx, row) in enumerate(test_sample.iterrows(), 1):
    variant_sku = row['Variant SKU']
    image_url = row['Design Image URL']
    
    start_time = time.time()
    print(f"\n[{i}/{len(test_sample)}] Analyzing {variant_sku}...")
    print(f"  URL: {image_url[:80]}...")
    
    pattern = analyze_image_with_ai(image_url)
    
    elapsed = time.time() - start_time
    print(f"  Completed in {elapsed:.1f} seconds")
    
    if pattern:
        print(f"  Pattern detected: {pattern}")
        results.append({
            'Variant SKU': variant_sku,
            'Product SKU': row['Product SKU'],
            'Original Patterns': row['Patterns'],
            'AI Detected Pattern': pattern,
            'Design Image URL': image_url
        })
    else:
        print(f"  Failed to detect pattern")
        results.append({
            'Variant SKU': variant_sku,
            'Product SKU': row['Product SKU'],
            'Original Patterns': row['Patterns'],
            'AI Detected Pattern': 'Error',
            'Design Image URL': image_url
        })
    
    # Add delay to avoid rate limiting (free tier: 5 requests/minute = 12 seconds minimum)
    # Wait 4 seconds between requests (15 requests/minute = 60/15 = 4 seconds)
    if i < len(test_sample):  # Don't wait after the last one
        print(f"  Waiting 4 seconds before next request...")
        time.sleep(4)

# Create results DataFrame
results_df = pd.DataFrame(results)

# Save test results (append if file exists, otherwise create new)
test_output_file = "../data/test_ai_pattern_results.csv"
if os.path.exists(test_output_file):
    # Append to existing file
    results_df.to_csv(test_output_file, mode='a', header=False, index=False, encoding='utf-8-sig')
    print(f"\n" + "="*60)
    print("TEST RESULTS APPENDED")
    print("="*60)
    print(f"Appended {len(results_df)} new results to: {test_output_file}")
else:
    # Create new file
    results_df.to_csv(test_output_file, index=False, encoding='utf-8-sig')
    print(f"\n" + "="*60)
    print("TEST RESULTS SAVED")
    print("="*60)
    print(f"Saved to: {test_output_file}")

# Display results
print("\n" + "="*60)
print("TEST RESULTS SUMMARY")
print("="*60)
print(results_df.to_string(index=False))

# Pattern distribution
print("\n" + "="*60)
print("PATTERN DISTRIBUTION")
print("="*60)
pattern_counts = results_df['AI Detected Pattern'].value_counts()
print(pattern_counts)

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
print(f"\nIf results look good, you can run the full extraction on all {len(df_with_images):,} rows.")

