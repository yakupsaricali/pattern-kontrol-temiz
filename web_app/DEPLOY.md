# Streamlit Cloud'a Deploy Talimatları

## Adım 1: GitHub Repository Oluşturma

1. [GitHub](https://github.com) hesabınıza giriş yapın
2. Sağ üstteki **"+"** butonuna tıklayın → **"New repository"**
3. Repository adı: `pattern-kontrol` (veya istediğiniz isim)
4. **Public** veya **Private** seçin (Streamlit Cloud her ikisini de destekler)
5. **"Create repository"** butonuna tıklayın

## Adım 2: Projeyi GitHub'a Yükleme

### Seçenek A: GitHub Desktop ile (Kolay)

1. [GitHub Desktop](https://desktop.github.com/) indirin ve kurun
2. GitHub Desktop'ta **"File" → "Clone repository"**
3. Oluşturduğunuz repository'yi seçin
4. Proje klasörünü (`yakup`) GitHub Desktop'a sürükleyin
5. **"Commit"** yapın (tüm değişiklikleri seçin)
6. **"Push origin"** ile GitHub'a yükleyin

### Seçenek B: Git Komut Satırı ile

Terminal'de şu komutları çalıştırın:

```bash
# Git başlat (eğer daha önce başlatılmadıysa)
cd C:\Users\BR\Desktop\yakup
git init

# GitHub repository'nizi ekleyin (URL'yi kendi repo'nuzla değiştirin)
git remote add origin https://github.com/KULLANICI_ADINIZ/pattern-kontrol.git

# Dosyaları ekle
git add .

# Commit yap
git commit -m "Initial commit: Pattern Kontrol Sistemi"

# GitHub'a yükle
git branch -M main
git push -u origin main
```

## Adım 3: Streamlit Cloud'a Bağlama

1. [streamlit.io/cloud](https://streamlit.io/cloud) adresine gidin
2. **"Sign up"** veya **"Sign in"** yapın (GitHub hesabınızla giriş yapabilirsiniz)
3. **"New app"** butonuna tıklayın
4. **"Repository"** kısmından GitHub repository'nizi seçin
5. **"Branch"**: `main` (veya `master`)
6. **"Main file path"**: `web_app/app.py` (önemli!)
7. **"App URL"**: İstediğiniz URL'i seçin (örn: `pattern-kontrol`)
8. **"Deploy!"** butonuna tıklayın

## Adım 4: Veri Dosyalarını Yükleme

Streamlit Cloud, CSV dosyalarınızı otomatik olarak görmeyebilir. İki seçenek var:

### Seçenek A: CSV'leri GitHub'a ekleyin (küçük dosyalar için)

```bash
# .gitignore'dan CSV'leri çıkarın (sadece data klasöründeki test_ai_pattern_results.csv için)
git add data/test_ai_pattern_results.csv
git commit -m "Add pattern data"
git push
```

### Seçenek B: Streamlit Secrets kullanın (büyük dosyalar için)

1. Streamlit Cloud'da **"Settings" → "Secrets"**
2. Veri dosyalarınızı başka bir yerde (Google Drive, S3, vb.) barındırın
3. URL'leri secrets'a ekleyin

## Adım 5: Uygulamayı Test Edin

1. Deploy tamamlandıktan sonra URL'nize gidin
2. Email ile giriş yapın
3. Pattern kontrolü yapın
4. Onay/Red butonlarını test edin

## Sorun Giderme

**"Module not found" hatası:**
- `requirements.txt` dosyasının `web_app/` klasöründe olduğundan emin olun
- Streamlit Cloud otomatik olarak `requirements.txt` dosyasını bulur

**"File not found" hatası:**
- `app.py` içindeki dosya yollarını kontrol edin
- `BASE_DIR = Path(__file__).parent.parent` doğru çalışıyor mu kontrol edin
- CSV dosyalarının GitHub'a yüklendiğinden emin olun

**"Port already in use" hatası:**
- Streamlit Cloud otomatik port yönetimi yapar, bu hata genelde olmaz
- Eğer olursa, Streamlit Cloud ayarlarından port'u değiştirin

## Domain

Streamlit Cloud otomatik olarak şu formatta bir domain verir:
`https://pattern-kontrol.streamlit.app`

Bu domain'i özelleştiremezsiniz, ama ücretsizdir ve SSL sertifikası otomatik eklenir.
