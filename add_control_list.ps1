# control_list_1000.csv dosyasını Git'e ekleme scripti
# Bu scripti GitHub Desktop'ta "Repository" > "Open in Command Prompt" ile açılan terminal'de çalıştırın

Write-Host "🔍 control_list_1000.csv dosyasını Git'e ekleniyor..." -ForegroundColor Yellow

# Dosya yolunu kontrol et
$filePath = "data\control_list_1000.csv"
if (Test-Path $filePath) {
    Write-Host "✅ Dosya bulundu: $filePath" -ForegroundColor Green
    
    # Git'e ekle (force)
    git add -f $filePath
    
    # Durumu kontrol et
    Write-Host "`n📋 Git durumu:" -ForegroundColor Cyan
    git status --short
    
    Write-Host "`n✅ Dosya Git'e eklendi! GitHub Desktop'ta 'Changes' sekmesinde görünmeli." -ForegroundColor Green
    Write-Host "💡 Şimdi GitHub Desktop'ta commit ve push yapabilirsiniz." -ForegroundColor Yellow
} else {
    Write-Host "❌ Dosya bulunamadı: $filePath" -ForegroundColor Red
    Write-Host "💡 Dosyayı önce kopyalayın: C:\Users\BR\Desktop\yakup\data\control_list_1000.csv" -ForegroundColor Yellow
}
