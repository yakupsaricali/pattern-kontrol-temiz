import pandas as pd
import requests
import os
import anthropic
import time
import base64
from PIL import Image
from io import BytesIO

print("="*60)
print("AI PATTERN EXTRACTION - CLAUDE 3.5 SONNET")
print("="*60)

# Configuration
TEST_SAMPLE_SIZE = 100
API_KEY_ENV = "ANTHROPIC_API_KEY"
MODEL_NAME = "claude-3-haiku-20240307"  # Claude 3 Haiku (çalışan model)

# API Key - Sadece environment variable kullan
# GÜVENLİK: API key'ler asla kod içinde saklanmamalı!
api_key = os.getenv(API_KEY_ENV)
if not api_key:
    print(f"\nWARNING: {API_KEY_ENV} environment variable not found.")
    print("Please set your Anthropic API key:")
    print(f"  Windows: set {API_KEY_ENV}=your_api_key_here")
    print(f"  Linux/Mac: export {API_KEY_ENV}=your_api_key_here")
    print("\nAlternatively, you can enter it when prompted.")
    api_key = input("Enter your Anthropic API key (or press Enter to skip): ").strip()
    if not api_key:
        print("Cannot proceed without API key. Exiting.")
        exit(1)
else:
    print(f"\nUsing API key from environment variable: {API_KEY_ENV}")

# Initialize Claude client
client = anthropic.Anthropic(api_key=api_key)

# Read the CSV file
print("\nReading CSV file...")
df = pd.read_csv('../data/rugs_empty_pattern_with_design_images_removedsames.csv')

# Filter to rows with design image URLs
df_with_images = df[df['Design Image URL'].notna() & (df['Design Image URL'] != '')].copy()
print(f"Total rows with design images: {len(df_with_images):,}")

# Get unique image URLs
unique_images = df_with_images['Design Image URL'].unique()
print(f"Unique image URLs: {len(unique_images):,}")

# Get unique URLs
df_unique = df_with_images.drop_duplicates(subset=['Design Image URL'], keep='first')

# Check if we have previous test results
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

# Take a test sample
test_sample = df_new.head(TEST_SAMPLE_SIZE).copy()
print(f"\nTest sample size: {len(test_sample)} rows (all NEW unique image URLs)")

# Function to analyze image with Claude
def analyze_image_with_claude(image_url, max_retries=3):
    """Use Claude API to analyze rug image and extract pattern"""
    
    for attempt in range(max_retries):
        try:
            # Download image from URL (increased timeout)
            img_response = requests.get(image_url, timeout=30)
            img_response.raise_for_status()
            
            # Resize image if too large (Claude has size limits - max 5MB base64)
            img_data = img_response.content
            img = Image.open(BytesIO(img_data))
                
            # Claude API limit: max 5MB base64 encoded image
            # Resize aggressively to ensure small size
            max_size = (1024, 1024)  # Smaller max dimensions for faster upload
            max_file_size = 3 * 1024 * 1024  # 3MB max (to account for base64 encoding overhead)
            
            # Resize if too large
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                print(f"  Image resized to {max_size}")
            
            # Convert to bytes with compression
            img_buffer = BytesIO()
            img_format = 'JPEG'  # Always use JPEG for smaller size
            if img.mode == 'RGBA':
                # Convert RGBA to RGB for JPEG
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[3])  # Use alpha channel as mask
                img = rgb_img
            
            # Save with quality optimization
            quality = 75  # Lower quality for smaller file size
            img.save(img_buffer, format=img_format, quality=quality, optimize=True)
            img_data = img_buffer.getvalue()
            
            # Check file size and reduce quality if needed
            while len(img_data) > max_file_size and quality > 30:
                quality -= 10
                img_buffer = BytesIO()
                img.save(img_buffer, format=img_format, quality=quality, optimize=True)
                img_data = img_buffer.getvalue()
                print(f"  Quality reduced to {quality}% (size: {len(img_data)/1024:.1f}KB)")
            
            print(f"  Final image size: {len(img_data)/1024:.1f}KB")
            
            # Prepare prompt - Sadece pattern adı isteniyor, açıklama YOK
            prompt = """Analyze this rug image and identify the VISUAL PATTERN type.

CRITICAL: Return ONLY the pattern name, nothing else. No explanations, no sentences, no descriptions. Just the pattern name.

PATTERNS (examples):
Geometric, Floral, Striped, Solid, Abstract, Medallion, Tribal, Chevron, Paisley, Damask, Ikat, Herringbone, Plaid, Checkered, Polka Dot, Animal Print

NOT STYLES (do not use): Oriental, Persian, Moroccan, Turkish, Traditional, Modern, Contemporary, Boho

Return format: Just the pattern name (e.g., "Damask" or "Geometric"). If unknown, return "Unknown".

Pattern:"""
            
            # Convert image to base64
            image_base64 = base64.b64encode(img_data).decode('utf-8')
            
            # Get content type based on format
            content_type = f'image/{img_format.lower()}'
            
            # Use Claude API
            message = client.messages.create(
                model=MODEL_NAME,
                max_tokens=10,  # Sadece pattern adı için yeterli
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": content_type,
                                    "data": image_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            pattern_text = message.content[0].text.strip()
            
            # Sadece pattern adını çıkar
            pattern_lines = pattern_text.split('\n')
            pattern = pattern_lines[0].strip()
            
            # Eğer cümle içinde pattern adı varsa, sadece adı çıkar
            import re
            pattern_names = ['Geometric', 'Floral', 'Striped', 'Solid', 'Abstract', 'Medallion', 
                           'Tribal', 'Chevron', 'Paisley', 'Damask', 'Ikat', 'Herringbone', 
                           'Plaid', 'Checkered', 'Polka Dot', 'Animal Print', 'Unknown']
            
            # Eğer yanıt uzunsa, pattern adını bul
            if len(pattern) > 20:
                for pname in pattern_names:
                    if pname.lower() in pattern.lower():
                        pattern = pname
                        break
                # Eğer bulunamazsa, ilk kelimeyi al
                if len(pattern) > 20:
                    pattern = pattern.split()[0] if pattern.split() else "Unknown"
            
            # Son kontrol: sadece pattern adı olmalı
            pattern = pattern.split('.')[0].split(',')[0].strip()
            
            return pattern
            
        except Exception as e:
            error_str = str(e)
            
            # Check for timeout/time-related errors
            is_timeout_error = (
                "timeout" in error_str.lower() or 
                "timed out" in error_str.lower() or
                "read timeout" in error_str.lower() or
                "connection" in error_str.lower() or
                "ssl" in error_str.lower()
            )
            
            if is_timeout_error:
                if attempt == 0:
                    wait_time = 15  # İlk hata: 15 saniye bekle
                    print(f"  Timeout error. Waiting {wait_time} seconds before retry {attempt + 2}/{max_retries}...")
                    time.sleep(wait_time)
                    continue
                elif attempt == 1:
                    wait_time = 30  # İkinci hata: 30 saniye bekle
                    print(f"  Timeout error again. Waiting {wait_time} seconds before retry {attempt + 2}/{max_retries}...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"  Timeout error after {max_retries} attempts: {error_str[:200]}")
                    return None
            
            # Check for rate limit/quota error
            if "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower():
                import re
                # Check if limit is 0
                if "limit: 0" in error_str or "limit:0" in error_str:
                    print(f"  [HATA] Bu model ucretsiz tier'da kullanilamiyor (limit: 0)")
                    return None
                
                retry_match = re.search(r'retry[_-]?after[:\s]+(\d+)', error_str, re.IGNORECASE)
                if retry_match:
                    retry_seconds = int(retry_match.group(1))
                    if attempt < max_retries - 1:
                        print(f"  Rate limit hit. Waiting {retry_seconds + 5} seconds before retry {attempt + 2}/{max_retries}...")
                        time.sleep(retry_seconds + 5)
                        continue
                else:
                    wait_time = 30 * (attempt + 1)
                    if attempt < max_retries - 1:
                        print(f"  Rate limit hit. Waiting {wait_time} seconds before retry {attempt + 2}/{max_retries}...")
                        time.sleep(wait_time)
                        continue
            
            # For other errors
            if attempt < max_retries - 1:
                wait_time = 3 * (attempt + 1)
                print(f"  Error (attempt {attempt + 1}/{max_retries}): {error_str[:100]}")
                print(f"  Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"  Error after {max_retries} attempts: {error_str[:200]}")
                return None
    
    return None

# Analyze images
print("\n" + "="*60)
print("ANALYZING IMAGES WITH CLAUDE AI")
print("="*60)

results = []
for i, (idx, row) in enumerate(test_sample.iterrows(), 1):
    variant_sku = row['Variant SKU']
    image_url = row['Design Image URL']
    
    start_time = time.time()
    print(f"\n[{i}/{len(test_sample)}] Analyzing {variant_sku}...")
    print(f"  URL: {image_url[:80]}...")
    
    pattern = analyze_image_with_claude(image_url)
    
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
    
    # Wait between requests (4 requests/minute = 15 seconds between requests)
    if i < len(test_sample):
        print(f"  Waiting 15 seconds before next image...")
        time.sleep(15)

# Save results
results_df = pd.DataFrame(results)
test_output_file = "../data/test_ai_pattern_results.csv"

if os.path.exists(test_output_file):
    results_df.to_csv(test_output_file, mode='a', header=False, index=False, encoding='utf-8-sig')
    print(f"\n" + "="*60)
    print("TEST RESULTS APPENDED")
    print("="*60)
    print(f"Appended {len(results_df)} new results to: {test_output_file}")
else:
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
