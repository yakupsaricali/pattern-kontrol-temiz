# Pattern Kontrol Sistemi - Web Uygulaması

Halı pattern'lerini kontrol etmek için mobil uyumlu web uygulaması.

## Özellikler

- ✅ Email ile giriş
- ✅ Mobil uyumlu arayüz
- ✅ Onay/Red butonları (swipe benzeri)
- ✅ Otomatik CSV kayıt sistemi
- ✅ İlerleme takibi

## Kurulum

### 1. Gerekli paketleri yükleyin

```bash
cd web_app
pip install -r requirements.txt
```

### 2. Uygulamayı çalıştırın

```bash
streamlit run app.py
```

Tarayıcıda otomatik olarak açılacaktır (genellikle `http://localhost:8501`)

## Kullanım

1. **Giriş**: Email adresinizi girin
2. **Kontrol**: Her halı için AI'nın tespit ettiği pattern'i görün
3. **Onay/Red**: Butonlara tıklayarak pattern'i onaylayın veya reddedin
4. **Kayıt**: Tüm onaylar ve redler otomatik olarak CSV dosyalarına kaydedilir

## Dosya Yapısı

```
web_app/
├── app.py                 # Ana uygulama
├── requirements.txt       # Python bağımlılıkları
├── .streamlit/
│   └── config.toml       # Streamlit ayarları
└── README.md             # Bu dosya

../data/
├── test_ai_pattern_results.csv    # Kaynak veri
├── approved_patterns.csv          # Onaylanan pattern'ler (otomatik oluşur)
└── rejected_patterns.csv          # Reddedilen pattern'ler (otomatik oluşur)
```

## Deploy (Yayınlama)

### Streamlit Cloud (Önerilen - Ücretsiz)

1. GitHub'a projeyi yükleyin
2. [streamlit.io/cloud](https://streamlit.io/cloud) adresine gidin
3. GitHub repo'nuzu bağlayın
4. `web_app/app.py` dosyasını seçin
5. Deploy edin!

**Domain**: `pattern-kontrol.streamlit.app` (otomatik)

### Render.com (Alternatif)

1. Render.com'da yeni Web Service oluşturun
2. GitHub repo'nuzu bağlayın
3. Build command: `pip install -r web_app/requirements.txt`
4. Start command: `cd web_app && streamlit run app.py --server.port=$PORT`
5. Deploy edin!

**Domain**: `pattern-kontrol.onrender.com`

### Railway.app (Alternatif)

1. Railway'de yeni proje oluşturun
2. GitHub repo'nuzu bağlayın
3. Environment variables ekleyin (gerekirse)
4. Deploy edin!

## Notlar

- Onaylanan ve reddedilen pattern'ler `data/` klasöründe ayrı CSV dosyalarına kaydedilir
- Her kayıt, kullanıcı email'i ve timestamp içerir
- Bir pattern bir kez kontrol edildikten sonra tekrar gösterilmez
- Mobil cihazlarda büyük butonlar ile kolay kullanım

## Sorun Giderme

**Dosya bulunamadı hatası:**
- `data/test_ai_pattern_results.csv` dosyasının varlığını kontrol edin
- Dosya yolu `../data/` şeklinde relative path kullanıyor

**Görsel yüklenemiyor:**
- İnternet bağlantınızı kontrol edin
- Görsel URL'lerinin erişilebilir olduğundan emin olun
