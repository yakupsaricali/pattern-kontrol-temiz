from google import genai
from google.genai import types

import os
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set!")
client = genai.Client(api_key=API_KEY)

# Test different models
models_to_test = [
    "models/gemini-1.5-flash",
    "models/gemini-2.5-flash",
    "models/gemini-flash-latest"
]

print("Model limitlerini test ediyoruz...\n")

for model_name in models_to_test:
    try:
        print(f"Test ediliyor: {model_name}")
        response = client.models.generate_content(
            model=model_name,
            contents=["Say 'test'"]
        )
        print(f"  ✓ Çalışıyor! Response: {response.text[:50]}\n")
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            print(f"  ✗ Model bulunamadı\n")
        elif "429" in error_msg or "quota" in error_msg.lower():
            print(f"  ⚠ Kota limiti - Model çalışıyor ama limit dolmuş\n")
        else:
            print(f"  ✗ Hata: {error_msg[:100]}\n")

print("\nNot: Gemini 1.5 Flash genellikle günde 1500 istek limiti var (ücretsiz tier)")
print("Gemini 2.5 Flash'ın limiti daha düşük olabilir (20/gün)")
