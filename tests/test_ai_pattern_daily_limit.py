import pandas as pd
import requests
import os
from google import genai
from google.genai import types
import time
from datetime import datetime

print("="*60)
print("AI PATTERN EXTRACTION - GÜNLÜK LİMİT KONTROLLÜ")
print("="*60)

# Configuration
# Günlük limit - API key'inize göre ayarlayın
# Google AI Studio'da kontrol edin: https://ai.dev/usage?tab=rate-limit
DAILY_LIMIT = 1500  # Eğer Gemini 1.5 Flash kullanıyorsanız 1500, yoksa 20
REQUESTS_PER_MINUTE = 15  # Dakikalık limit
DELAY_SECONDS = 60 / REQUESTS_PER_MINUTE  # 4 saniye

import os
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set!")
MODEL_NAME = "models/gemini-2.5-flash"  # Mevcut model

# Bugünkü istek sayısını kontrol et
def get_today_request_count():
    """Bugün yapılan istek sayısını kontrol et"""
    if not os.path.exists('test_ai_pattern_results.csv'):
        return 0
    
    try:
        df = pd.read_csv('test_ai_pattern_results.csv')
        if 'AI Detected Pattern' in df.columns:
            # Bugünkü kayıtları say (basit yöntem - timestamp eklenebilir)
            # Şimdilik tüm kayıtları sayıyoruz, ama günlük limiti aşmamak için
            # sadece bugünkü kayıtları saymak daha iyi olur
            return len(df)
    except:
        return 0
    return 0

# Initialize
client = genai.Client(api_key=API_KEY)

# Bugünkü istek sayısını kontrol et
today_count = get_today_request_count()
remaining = DAILY_LIMIT - today_count

print(f"\nBugünkü istek sayısı: {today_count}")
print(f"Kalan istek hakkı: {remaining}")
print(f"Dakikalık limit: {REQUESTS_PER_MINUTE} istek/dakika")
print(f"İstekler arası bekleme: {DELAY_SECONDS:.1f} saniye\n")

if remaining <= 0:
    print("⚠️  GÜNLÜK LİMİT DOLDU!")
    print("Yarın tekrar deneyin veya ücretli plana geçin.")
    exit(1)

# Kaç istek yapılacak?
MAX_REQUESTS = min(remaining, 15)  # Maksimum 15 istek (veya kalan kadar)
print(f"Bu çalıştırmada {MAX_REQUESTS} istek yapılacak.\n")

# Read CSV
print("CSV dosyası okunuyor...")
df = pd.read_csv('rugs_empty_pattern_with_design_images.csv')
df_with_images = df[df['Design Image URL'].notna() & (df['Design Image URL'] != '')].copy()
print(f"Toplam {len(df_with_images):,} satır bulundu")

# Get unique URLs
df_unique = df_with_images.drop_duplicates(subset=['Design Image URL'], keep='first')

# Skip already tested
tested_urls = set()
if os.path.exists('test_ai_pattern_results.csv'):
    try:
        prev = pd.read_csv('test_ai_pattern_results.csv')
        if 'Design Image URL' in prev.columns:
            tested_urls = set(prev['Design Image URL'].dropna())
            print(f"{len(tested_urls)} zaten test edilmiş URL atlanıyor")
    except:
        pass

df_new = df_unique[~df_unique['Design Image URL'].isin(tested_urls)].copy()
test_sample = df_new.head(MAX_REQUESTS).copy()
print(f"\n{len(test_sample)} YENİ görsel işlenecek\n")

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
        print("  Gemini API çağrılıyor...")
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
            print(f"  [KOTA LİMİTİ] Günlük limit aşıldı!")
            print(f"  Detay: {error_msg}")
            pattern = 'QuotaExceeded'
            break  # Stop processing
        else:
            print(f"  [HATA] {error_msg} ({elapsed:.1f}s)")
            pattern = 'Error'
    
    results.append({
        'Variant SKU': variant_sku,
        'Product SKU': row['Product SKU'],
        'Original Patterns': row['Patterns'],
        'AI Detected Pattern': pattern,
        'Design Image URL': image_url,
        'Processed Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    
    # Wait between requests (4 seconds for 15 requests/minute)
    if i < len(test_sample) and pattern != 'QuotaExceeded':
        print(f"  {DELAY_SECONDS:.1f} saniye bekleniyor...\n")
        time.sleep(DELAY_SECONDS)

# Save results
if results:
    results_df = pd.DataFrame(results)
    output_file = "test_ai_pattern_results.csv"
    
    if os.path.exists(output_file):
        results_df.to_csv(output_file, mode='a', header=False, index=False, encoding='utf-8-sig')
        print(f"\n✓ {len(results_df)} sonuç eklendi: {output_file}")
    else:
        results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n✓ {len(results_df)} sonuç kaydedildi: {output_file}")
    
    total_time = time.time() - start_total
    print(f"\n{'='*60}")
    print(f"TAMAMLANDI - Toplam süre: {total_time/60:.1f} dakika")
    print(f"{'='*60}")
    print("\nSonuçlar:")
    print(results_df[['Variant SKU', 'AI Detected Pattern']].to_string(index=False))
    print(f"\nPattern dağılımı:")
    print(results_df['AI Detected Pattern'].value_counts())
    
    # Kalan istek hakkı
    new_count = get_today_request_count()
    remaining_after = DAILY_LIMIT - new_count
    print(f"\nKalan günlük istek hakkı: {remaining_after}/{DAILY_LIMIT}")
else:
    print("\nHiç sonuç kaydedilmedi.")
