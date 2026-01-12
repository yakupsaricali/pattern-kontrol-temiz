import anthropic
import os

# API Key - Environment variable kullan (güvenlik için)
API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not API_KEY:
    raise ValueError("ANTHROPIC_API_KEY environment variable not set!")
client = anthropic.Anthropic(api_key=API_KEY)

# Tüm olası Claude model isimleri
models_to_test = [
    "claude-3-haiku-20240307",  # Bu çalıştı
    "claude-3-5-haiku-20241022",
    "claude-3-5-haiku-20240620",
    "claude-3-sonnet-20240229",
    "claude-3-5-sonnet-20240620",
    "claude-3-5-sonnet-20241022",
    "claude-3-opus-20240229",
    "claude-3-5-opus-20240620",
    "claude-3-5-opus-20241022",
]

print("Erisilebilir Claude modellerini test ediyoruz...\n")
working_models = []

for model_name in models_to_test:
    try:
        print(f"Test: {model_name}...", end=" ")
        response = client.messages.create(
            model=model_name,
            max_tokens=5,
            messages=[{"role": "user", "content": "hi"}]
        )
        print(f"[OK] Calisiyor!")
        working_models.append(model_name)
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not_found" in error_msg.lower():
            print("[BULUNAMADI]")
        else:
            print(f"[HATA] {str(e)[:50]}")

print(f"\n{'='*60}")
print(f"Calisan modeller ({len(working_models)}):")
for model in working_models:
    print(f"  - {model}")
