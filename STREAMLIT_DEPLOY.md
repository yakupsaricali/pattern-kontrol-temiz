# 🚀 Streamlit Cloud'a Hızlı Deploy Rehberi

## ⚡ Hızlı Başlangıç (5 Dakika)

### 1️⃣ GitHub Repository Oluştur
1. [github.com](https://github.com) → **New repository**
2. İsim: `pattern-kontrol` 
3. **Create repository**

### 2️⃣ Projeyi GitHub'a Yükle

**GitHub Desktop ile (En Kolay):**
1. [GitHub Desktop](https://desktop.github.com/) indir
2. Repository'yi clone et
3. `yakup` klasörünü repository klasörüne kopyala
4. Commit + Push

**Veya Git ile:**
```bash
cd C:\Users\BR\Desktop\yakup
git init
git add .
git commit -m "Pattern Kontrol Sistemi"
git remote add origin https://github.com/KULLANICI_ADINIZ/pattern-kontrol.git
git push -u origin main
```

### 3️⃣ Streamlit Cloud'a Deploy Et
1. [streamlit.io/cloud](https://streamlit.io/cloud) → **Sign in** (GitHub ile)
2. **New app** → Repository seç
3. **Main file path**: `web_app/app.py` ⚠️ (ÖNEMLİ!)
4. **Deploy!**

### 4️⃣ Domain
Otomatik domain: `https://pattern-kontrol.streamlit.app`

---

## 📋 Detaylı Talimatlar

Detaylar için `web_app/DEPLOY.md` dosyasına bakın.

## ⚠️ Önemli Notlar

- **Main file path** mutlaka `web_app/app.py` olmalı
- CSV dosyalarını GitHub'a yüklemeyi unutmayın (küçük dosyalar için)
- Büyük CSV dosyaları için alternatif depolama kullanın
