# Render'a Deploy Rehberi

## Repository: pattern-kontrol-temiz

## 1. GitHub'a Push (GitHub Desktop ile)
1. GitHub Desktop'ı açın
2. Repository: `pattern-kontrol-temiz` seçin
3. Değişiklikleri görün:
   - `web_app/app_flask.py` (Flask uygulaması)
   - `web_app/Procfile` (yeni)
   - `web_app/runtime.txt` (yeni)
   - `web_app/requirements.txt` (güncellenmiş)
4. Summary: "Flask app with swipe, authentication, and results"
5. "Commit to main" → "Push origin"

## 2. Render'a Giriş
1. [render.com](https://render.com) adresine gidin
2. "Get Started for Free" butonuna tıklayın
3. GitHub hesabınızla giriş yapın

## 3. Yeni Web Service Oluştur
1. Dashboard'da "New +" butonuna tıklayın
2. "Web Service" seçin
3. GitHub repository: **`pattern-kontrol-temiz`** seçin

## 4. Ayarları Yapılandır
- **Name**: `pattern-kontrol` (veya istediğiniz isim)
- **Region**: `Frankfurt` (veya size yakın)
- **Branch**: `main`
- **Root Directory**: `web_app` ⚠️ (ÖNEMLİ!)
- **Runtime**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python app_flask.py`

## 5. Environment Variables
Şu an gerekli değişken yok. (API key'ler kodda yok, güvenli ✅)

## 6. Deploy
"Create Web Service" butonuna tıklayın. İlk deploy 2-3 dakika sürebilir.

## 7. URL
Deploy tamamlandığında şu formatta bir URL alacaksınız:
```
https://pattern-kontrol.onrender.com
```

## Önemli Notlar
- **Ücretsiz tier**: 15 dakika kullanılmazsa uyku moduna geçer (ilk istekte uyanır)
- **HTTPS**: Otomatik olarak HTTPS aktif
- **Auto-deploy**: GitHub'a push yaptığınızda otomatik deploy olur

## Sorun Giderme
- Logs: Render dashboard'da "Logs" sekmesinden hataları görebilirsiniz
- Build hatası: `requirements.txt` dosyasını kontrol edin
- Port hatası: `app_flask.py` dosyasında `PORT` environment variable kullanılıyor
