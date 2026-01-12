import anthropic
import os

# API Key - Environment variable kullan (güvenlik için)
API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not API_KEY:
    raise ValueError("ANTHROPIC_API_KEY environment variable not set!")
client = anthropic.Anthropic(api_key=API_KEY)

# Test different model names
models_to_test = [
    "claude-sonnet-4",
    "claude-sonnet-4.5",
    "claude-4-sonnet",
    "claude-4-5-sonnet",
    "claude-sonnet-4-20241022",
    "claude-sonnet-4.5-20241022",
    "claude-3-5-sonnet-20240620",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-latest"
]

print("Claude modellerini test ediyoruz...\n")

for model_name in models_to_test:
    try:
        print(f"Test ediliyor: {model_name}")
        response = client.messages.create(
            model=model_name,
            max_tokens=10,
            messages=[{"role": "user", "content": "Say 'test'"}]
        )
        print(f"  [OK] Calisiyor! Response: {response.content[0].text}\n")
        break  # İlk çalışan modeli bulduk
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not_found" in error_msg.lower():
            print(f"  [HATA] Model bulunamadi\n")
        else:
            print(f"  [HATA] {error_msg[:100]}\n")
