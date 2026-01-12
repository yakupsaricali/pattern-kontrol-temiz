from google import genai
from google.genai import types
import requests
from io import BytesIO

import os
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set!")
client = genai.Client(api_key=API_KEY)

# Test edilecek modeller
models_to_test = [
    "models/gemini-2.5-flash",
    "models/gemini-exp-1206",
    "models/gemini-1.5-flash"  # Erişilemiyor ama deneyelim
]

print("="*60)
print("MODEL LİMİTLERİNİ KONTROL EDİYORUZ")
print("="*60)

# Test için küçük bir görsel URL'i kullan
test_image_url = "https://brugs-image.s3.us-east-2.amazonaws.com/223281/223281-003_prm_1.jpg"

for model_name in models_to_test:
    print(f"\n{'='*60}")
    print(f"Model: {model_name}")
    print(f"{'='*60}")
    
    try:
        # Görseli indir
        img_resp = requests.get(test_image_url, timeout=5)
        img_resp.raise_for_status()
        
        # Image part oluştur
        image_part = types.Part.from_bytes(
            data=img_resp.content,
            mime_type="image/jpeg"
        )
        
        # Test isteği
        prompt = "Say 'test'"
        print("Test isteği gönderiliyor...")
        
        response = client.models.generate_content(
            model=model_name,
            contents=[prompt, image_part]
        )
        
        print(f"[OK] BASARILI - Model calisiyor!")
        print(f"  Response: {response.text[:50]}")
        print(f"  Limit bilgisi: Hata mesajından öğrenilemez (başarılı)")
        
    except Exception as e:
        error_msg = str(e)
        
        # 404 - Model bulunamadı
        if "404" in error_msg or "not found" in error_msg.lower():
            print(f"[HATA] Model bulunamadı veya erisilemiyor")
        
        # 429 - Limit aşıldı (bu durumda limit bilgisi var)
        elif "429" in error_msg or "quota" in error_msg.lower() or "limit" in error_msg.lower():
            print(f"[KOTA LIMITI] Limit bilgisi:")
            
            # Limit bilgilerini çıkar
            import re
            
            # Günlük limit
            daily_match = re.search(r'limit:\s*(\d+)', error_msg)
            if daily_match:
                print(f"  Günlük limit: {daily_match.group(1)} istek/gün")
            
            # Dakikalık limit
            per_min_match = re.search(r'(\d+)\s*requests?\s*per\s*minute', error_msg, re.IGNORECASE)
            if per_min_match:
                print(f"  Dakikalık limit: {per_min_match.group(1)} istek/dakika")
            
            # Retry bilgisi
            retry_match = re.search(r'retry in (\d+)', error_msg)
            if retry_match:
                print(f"  Tekrar deneme: {retry_match.group(1)} saniye sonra")
            
            # Tam hata mesajı
            print(f"\n  Detaylı hata:")
            print(f"  {error_msg[:300]}")
        
        # Diğer hatalar
        else:
            print(f"[HATA] {error_msg[:200]}")

print(f"\n{'='*60}")
print("NOT: Limit bilgileri Google AI Studio'da da kontrol edilebilir:")
print("https://ai.dev/usage?tab=rate-limit")
print("="*60)
