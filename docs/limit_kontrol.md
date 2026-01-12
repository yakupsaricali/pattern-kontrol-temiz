# Gemini API Limit Kontrolü

## Mevcut Durum
- **Kullandığımız Model**: `models/gemini-2.5-flash`
- **Hata Mesajı**: Günlük limit 20 istek (ücretsiz tier)

## Limit Kontrolü

### 1. Google AI Studio'da Kontrol Edin
1. https://ai.dev/usage?tab=rate-limit adresine gidin
2. API key'inizi seçin
3. Hangi modelin hangi limiti olduğunu görün

### 2. Farklı Modeller ve Limitleri

**Gemini 1.5 Flash** (eğer erişiminiz varsa):
- Ücretsiz tier: **1500 istek/gün**
- Dakikalık: 15 istek/dakika

**Gemini 2.5 Flash** (şu an kullandığımız):
- Ücretsiz tier: **20 istek/gün** (görünüşe göre)
- Dakikalık: 15 istek/dakika

### 3. Çözüm Önerileri

**Seçenek 1: Gemini 1.5 Flash'a Erişim**
- Google AI Studio'da Gemini 1.5 Flash modeline erişiminiz var mı kontrol edin
- Varsa, model adını `models/gemini-1.5-flash` olarak değiştirin
- Limit 1500/gün olacak

**Seçenek 2: API Key Tier Kontrolü**
- API key'iniz ücretsiz tier'da mı yoksa ücretli tier'da mı?
- Ücretli tier'da limitler çok daha yüksek

**Seçenek 3: Farklı Model Deneyin**
- `models/gemini-flash-latest` - Bu genellikle en son Flash versiyonunu kullanır
- Limitleri farklı olabilir

## Hızlı Test

Limitinizi test etmek için:
```bash
python test_ai_pattern_daily_limit.py
```

Script otomatik olarak kalan istek hakkınızı gösterecek.
