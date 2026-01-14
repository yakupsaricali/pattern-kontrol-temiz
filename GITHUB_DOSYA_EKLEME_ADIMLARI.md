# control_list_1000.csv Dosyasını GitHub'a Ekleme - Adım Adım

## ✅ Dosya Durumu

- ✅ Dosya GitHub repo'da mevcut: `C:\Users\BR\Documents\GitHub\pattern-kontrol-temiz\data\control_list_1000.csv`
- ✅ Dosya içeriği: 1000 satır, doğru format
- ✅ `.gitignore` dosyasında exception olarak eklenmiş

## 🔧 GitHub Desktop'ta Görünmüyorsa - Çözüm

### Yöntem 1: PowerShell Script ile (Önerilen)

1. GitHub Desktop'ı açın
2. Repository: **pattern-kontrol-temiz** seçili olmalı
3. "Repository" > "Open in Command Prompt" (veya "Open in PowerShell")
4. Şu komutu çalıştırın:

```powershell
.\add_control_list.ps1
```

5. Script dosyayı Git'e ekleyecek
6. GitHub Desktop'ta "Changes" sekmesinde dosya görünmeli

### Yöntem 2: Manuel Komut ile

GitHub Desktop'ta "Repository" > "Open in Command Prompt" ile terminal açın:

```powershell
cd "C:\Users\BR\Documents\GitHub\pattern-kontrol-temiz"
git add -f data/control_list_1000.csv
git status
```

### Yöntem 3: GitHub Desktop'ta Refresh

1. GitHub Desktop'ı kapatıp tekrar açın
2. "Repository" > "Refresh" yapın (veya F5)
3. "Changes" sekmesini kontrol edin

### Yöntem 4: Dosyayı Silip Tekrar Ekleme

Eğer hiçbiri işe yaramazsa:

1. GitHub Desktop'ta "Repository" > "Show in Explorer"
2. `data/control_list_1000.csv` dosyasını silin (yedek alın!)
3. Dosyayı tekrar kopyalayın:
   ```powershell
   Copy-Item "C:\Users\BR\Desktop\yakup\data\control_list_1000.csv" -Destination "C:\Users\BR\Documents\GitHub\pattern-kontrol-temiz\data\control_list_1000.csv"
   ```
4. GitHub Desktop'ta "Changes" sekmesinde dosya görünmeli

## 📋 Commit ve Push

Dosya "Changes" sekmesinde göründükten sonra:

1. Commit mesajı: "Add control_list_1000.csv file (1000 unchecked products)"
2. "Commit to main" butonuna tıklayın
3. "Push origin" butonuna tıklayın

## ✅ Kontrol

GitHub web sitesinde:
1. Repository'nizi açın: `https://github.com/[kullanıcı-adı]/pattern-kontrol-temiz`
2. `data/control_list_1000.csv` dosyasının orada olduğunu kontrol edin
3. Dosyayı açıp 1000 satır olduğunu doğrulayın
