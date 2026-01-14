from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for, send_file
import pandas as pd
from pathlib import Path
from datetime import datetime
import secrets
import os
import io
from sqlalchemy import create_engine, Column, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Session için secret key

# PostgreSQL bağlantısı
DATABASE_URL = os.environ.get('DATABASE_URL')
USE_DATABASE = False
engine = None
SessionLocal = None

if DATABASE_URL:
    try:
        # Render PostgreSQL URL'i genellikle postgres:// ile başlar, SQLAlchemy postgresql:// istiyor
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        SessionLocal = sessionmaker(bind=engine)
        USE_DATABASE = True
        print("✅ PostgreSQL veritabanı kullanılıyor")
    except Exception as e:
        print(f"❌ PostgreSQL bağlantı hatası: {e}")
        USE_DATABASE = False

# Veritabanı modelleri
Base = declarative_base()

class PatternReview(Base):
    __tablename__ = 'pattern_reviews'
    
    id = Column(String, primary_key=True)  # Variant SKU
    variant_sku = Column(String, nullable=False)
    product_sku = Column(String)
    ai_pattern = Column(Text)
    image_url = Column(Text)
    status = Column(String, nullable=False)  # 'Approved' or 'Rejected'
    reviewed_by = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

# Tabloları oluştur
if USE_DATABASE:
    try:
        Base.metadata.create_all(engine)
        print("✅ Veritabanı tabloları hazır")
    except Exception as e:
        print(f"❌ Tablo oluşturma hatası: {e}")

# Dosya yolları - Sadece pattern yükleme için
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONTROL_LIST_FILE = DATA_DIR / "control_list_1000.csv"  # Kontrol listesi dosyası (1000 ürün)
FALLBACK_PATTERNS_FILE = DATA_DIR / "test_ai_pattern_results.csv"  # Fallback dosya
# Önce control_list_1000.csv'yi dene, yoksa test_ai_pattern_results.csv'yi kullan
PATTERNS_FILE = CONTROL_LIST_FILE if CONTROL_LIST_FILE.exists() else FALLBACK_PATTERNS_FILE

# Global state
patterns_data = None
reviewed_skus = set()  # Global olarak kontrol edilen tüm SKU'lar

def load_patterns():
    """Pattern dosyasını yükle - önce control_list_1000.csv, yoksa test_ai_pattern_results.csv"""
    global patterns_data, PATTERNS_FILE
    
    # Önce control_list_1000.csv'yi kontrol et
    if not CONTROL_LIST_FILE.exists():
        print(f"⚠️ DEBUG load_patterns: control_list_1000.csv bulunamadı, test_ai_pattern_results.csv kullanılıyor")
        PATTERNS_FILE = FALLBACK_PATTERNS_FILE
    else:
        PATTERNS_FILE = CONTROL_LIST_FILE
        print(f"✅ DEBUG load_patterns: control_list_1000.csv bulundu, kullanılıyor")
    
    print(f"🔍 DEBUG load_patterns: PATTERNS_FILE = {PATTERNS_FILE}")
    print(f"🔍 DEBUG load_patterns: Dosya var mı? {PATTERNS_FILE.exists()}")
    
    if not PATTERNS_FILE.exists():
        print(f"❌ DEBUG: Dosya bulunamadı: {PATTERNS_FILE}")
        return None
    
    try:
        df = pd.read_csv(PATTERNS_FILE, encoding='utf-8-sig', on_bad_lines='skip', low_memory=False)
        print(f"🔍 DEBUG load_patterns: Dosya yüklendi, {len(df)} satır")
        expected_columns = ['Variant SKU', 'Product SKU', 'Original Patterns', 'AI Detected Pattern', 'Design Image URL']
        if len(df.columns) > len(expected_columns):
            if 'AI Detected Pattern' in df.columns:
                extra_cols = df.columns[len(expected_columns):]
                for col in extra_cols:
                    df['AI Detected Pattern'] = df['AI Detected Pattern'].astype(str) + ', ' + df[col].astype(str)
                df = df[expected_columns]
        if len(df.columns) >= len(expected_columns):
            df.columns = expected_columns[:len(df.columns)]
        df = df.dropna(subset=['Variant SKU', 'Design Image URL'])
        patterns_data = df
        print(f"✅ DEBUG load_patterns: {len(df)} ürün yüklendi")
        return df
    except Exception as e:
        print(f"❌ Hata: {e}")
        import traceback
        traceback.print_exc()
        return None

def load_reviewed_skus():
    """Veritabanından veya CSV'den kontrol edilmiş SKU'ları yükle (sadece mevcut pattern dosyasındaki SKU'lar)"""
    global reviewed_skus, patterns_data
    reviewed = set()
    
    # Önce patterns_data'yı yükle (hangi SKU'ların mevcut olduğunu bilmek için)
    if patterns_data is None:
        load_patterns()
    
    # Mevcut pattern dosyasındaki SKU'ları al
    current_skus = set()
    if patterns_data is not None and len(patterns_data) > 0:
        current_skus = set(patterns_data['Variant SKU'].astype(str))
    
    print(f"🔍 DEBUG load_reviewed_skus: Mevcut pattern dosyasında {len(current_skus)} SKU var")
    
    if USE_DATABASE:
        # Veritabanından oku (web uygulaması veritabanı kullanıyorsa)
        try:
            db_session = SessionLocal()
            reviews = db_session.query(PatternReview).all()
            # Sadece mevcut pattern dosyasındaki SKU'ları al
            reviewed = {str(review.variant_sku) for review in reviews if str(review.variant_sku) in current_skus}
            db_session.close()
            print(f"🔍 DEBUG load_reviewed_skus: Veritabanından {len(reviewed)} SKU bulundu (mevcut dosyada)")
        except Exception as e:
            print(f"❌ Veritabanı okuma hatası: {e}")
            import traceback
            traceback.print_exc()
    else:
        # Fallback: CSV dosyalarından oku (local development)
        approved_file = DATA_DIR / "approved_patterns.csv"
        rejected_file = DATA_DIR / "rejected_patterns.csv"
        
        if approved_file.exists():
            try:
                approved_df = pd.read_csv(approved_file, encoding='utf-8-sig', on_bad_lines='skip')
                if 'Variant SKU' in approved_df.columns:
                    approved_skus = set(approved_df['Variant SKU'].dropna().astype(str))
                    # Sadece mevcut pattern dosyasındaki SKU'ları al
                    reviewed.update(approved_skus & current_skus)
                    print(f"🔍 DEBUG load_reviewed_skus: approved_patterns.csv'den {len(approved_skus & current_skus)} SKU bulundu")
            except Exception as e:
                print(f"❌ Approved CSV okuma hatası: {e}")
                import traceback
                traceback.print_exc()
        
        if rejected_file.exists():
            try:
                rejected_df = pd.read_csv(rejected_file, encoding='utf-8-sig', on_bad_lines='skip')
                if 'Variant SKU' in rejected_df.columns:
                    rejected_skus = set(rejected_df['Variant SKU'].dropna().astype(str))
                    # Sadece mevcut pattern dosyasındaki SKU'ları al
                    reviewed.update(rejected_skus & current_skus)
                    print(f"🔍 DEBUG load_reviewed_skus: rejected_patterns.csv'den {len(rejected_skus & current_skus)} SKU bulundu")
            except Exception as e:
                print(f"❌ Rejected CSV okuma hatası: {e}")
                import traceback
                traceback.print_exc()
    
    reviewed_skus = reviewed
    print(f"✅ DEBUG load_reviewed_skus: Toplam {len(reviewed)} SKU kontrol edilmiş olarak işaretlendi (sadece mevcut dosyadan)")
    return reviewed

def get_current_pattern():
    """Kullanıcı bazlı pattern döndür (her kullanıcı farklı pattern görür)"""
    global patterns_data, reviewed_skus
    
    if patterns_data is None:
        load_patterns()
        load_reviewed_skus()
    
    print(f"🔍 DEBUG get_current_pattern: patterns_data boyutu = {len(patterns_data) if patterns_data is not None else 0}")
    print(f"🔍 DEBUG get_current_pattern: reviewed_skus boyutu = {len(reviewed_skus)}")
    
    if patterns_data is None or len(patterns_data) == 0:
        print(f"❌ DEBUG get_current_pattern: patterns_data boş!")
        return None
    
    # Kullanıcı bazlı current_index (session'da saklanır)
    user_email = session.get('email', 'unknown')
    current_index = session.get(f'current_index_{user_email}', 0)
    
    # Filtrele: Hem global olarak reviewed olanları hem de "Error" pattern'lerini atla
    df = patterns_data[
        ~patterns_data['Variant SKU'].astype(str).isin(reviewed_skus) &
        (patterns_data['AI Detected Pattern'].astype(str).str.strip().str.upper() != 'ERROR')
    ].copy()
    
    print(f"🔍 DEBUG get_current_pattern: Filtreleme sonrası {len(df)} ürün kaldı")
    
    if len(df) == 0:
        print(f"❌ DEBUG get_current_pattern: Filtreleme sonrası hiç ürün kalmadı!")
        print(f"🔍 DEBUG: İlk 5 reviewed SKU: {list(reviewed_skus)[:5]}")
        print(f"🔍 DEBUG: İlk 5 pattern SKU: {list(patterns_data['Variant SKU'].astype(str))[:5]}")
        return None
    
    # Index'i sınırla
    if current_index >= len(df):
        current_index = 0
        session[f'current_index_{user_email}'] = 0
    
    current_row = df.iloc[current_index]
    return {
        'variant_sku': current_row['Variant SKU'],
        'product_sku': current_row['Product SKU'],
        'ai_pattern': current_row['AI Detected Pattern'],
        'image_url': current_row['Design Image URL'],
        'total': len(patterns_data),
        'reviewed': len(reviewed_skus),
        'remaining': len(df)
    }

def save_review(variant_sku, product_sku, ai_pattern, image_url, approved=True):
    """Veritabanına kaydet veya CSV'ye (fallback)"""
    timestamp = datetime.utcnow()
    user_email = session.get('email', 'unknown')
    status = 'Approved' if approved else 'Rejected'
    
    if USE_DATABASE:
        try:
            db_session = SessionLocal()
            # Mevcut kaydı kontrol et
            existing = db_session.query(PatternReview).filter_by(variant_sku=str(variant_sku)).first()
            if existing:
                # Güncelle
                existing.product_sku = product_sku
                existing.ai_pattern = ai_pattern
                existing.image_url = image_url
                existing.status = status
                existing.reviewed_by = user_email
                existing.timestamp = timestamp
            else:
                # Yeni kayıt
                review = PatternReview(
                    id=str(variant_sku),
                    variant_sku=str(variant_sku),
                    product_sku=product_sku,
                    ai_pattern=ai_pattern,
                    image_url=image_url,
                    status=status,
                    reviewed_by=user_email,
                    timestamp=timestamp
                )
                db_session.add(review)
            db_session.commit()
            db_session.close()
            reviewed_skus.add(str(variant_sku))
            print(f"✅ Kayıt veritabanına kaydedildi: {variant_sku} - {status}")
        except Exception as e:
            print(f"❌ Veritabanı kayıt hatası: {e}")
    else:
        # Fallback: CSV'ye kaydet
        filename = DATA_DIR / ("approved_patterns.csv" if approved else "rejected_patterns.csv")
        data = {
            'Variant SKU': variant_sku,
            'Product SKU': product_sku,
            'AI Detected Pattern': ai_pattern,
            'Design Image URL': image_url,
            'Status': status,
            'Reviewed By': user_email,
            'Timestamp': timestamp.isoformat()
        }
        df = pd.DataFrame([data])
        if filename.exists():
            df.to_csv(filename, mode='a', header=False, index=False, encoding='utf-8-sig')
        else:
            df.to_csv(filename, index=False, encoding='utf-8-sig')
        reviewed_skus.add(str(variant_sku))

# İlk yükleme
load_patterns()
load_reviewed_skus()

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Giriş - Pattern Kontrol Sistemi</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1rem;
        }
        .login-container {
            background: white;
            border-radius: 20px;
            padding: 2rem;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            max-width: 400px;
            width: 100%;
        }
        h1 { text-align: center; color: #333; margin-bottom: 0.5rem; }
        .subtitle { text-align: center; color: #666; font-size: 0.9rem; margin-bottom: 2rem; }
        .form-group {
            margin-bottom: 1.5rem;
        }
        label {
            display: block;
            margin-bottom: 0.5rem;
            color: #333;
            font-weight: 500;
        }
        input[type="email"] {
            width: 100%;
            padding: 1rem;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 1rem;
            transition: border-color 0.3s;
        }
        input[type="email"]:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn-login {
            width: 100%;
            padding: 1rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 1.1rem;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .btn-login:hover {
            transform: scale(1.02);
        }
        .btn-login:active {
            transform: scale(0.98);
        }
        .error {
            background: #ffebee;
            color: #c62828;
            padding: 0.8rem;
            border-radius: 10px;
            margin-bottom: 1rem;
            text-align: center;
        }
        .info {
            background: #e3f2fd;
            color: #1976d2;
            padding: 0.8rem;
            border-radius: 10px;
            margin-top: 1rem;
            text-align: center;
            font-size: 0.9rem;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>🔐 Giriş</h1>
        <p class="subtitle">Pattern Kontrol Sistemi</p>
        
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        
        <form method="POST" action="/login">
            <div class="form-group">
                <label for="email">Email Adresiniz</label>
                <input type="email" id="email" name="email" placeholder="Email adresinizi girin" required autofocus>
            </div>
            <button type="submit" class="btn-login">Giriş Yap</button>
        </form>
        
        <div class="info">
            ⓘ Geçerli email adresinizi girin.
        </div>
    </div>
</body>
</html>
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pattern Kontrol Sistemi</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 1rem;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 1.5rem;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        h1 { text-align: center; color: #333; margin-bottom: 0.5rem; }
        .subtitle { text-align: center; color: #666; font-size: 0.9rem; margin-bottom: 1rem; }
        .progress {
            background: #e3f2fd;
            padding: 0.8rem;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 1rem;
            font-weight: bold;
        }
        .image-container {
            position: relative;
            width: 100%;
            margin: 1rem 0;
            touch-action: pan-y;
        }
        .swipe-indicator {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            font-size: 5rem;
            opacity: 0;
            transition: opacity 0.3s;
            z-index: 10;
            pointer-events: none;
            font-weight: bold;
        }
        .swipe-indicator.left { left: 20px; color: #f44336; }
        .swipe-indicator.right { right: 20px; color: #4CAF50; }
        .swipe-indicator.active { opacity: 0.9; }
        .rug-image {
            width: 100%;
            max-height: 400px;
            object-fit: contain;
            border-radius: 10px;
            display: block;
            margin: 0 auto;
            touch-action: pan-y;
            cursor: pointer;
        }
        .info-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem;
            border-radius: 10px;
            margin: 1rem 0;
            text-align: center;
        }
        .info-box h3 { font-size: 1.5rem; margin-bottom: 0.5rem; }
        .info-box p { font-size: 0.9rem; opacity: 0.9; }
        .buttons {
            display: flex;
            gap: 1rem;
        }
        .btn {
            flex: 1;
            padding: 1.2rem;
            font-size: 1.3rem;
            font-weight: bold;
            border: none;
            border-radius: 15px;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn:active { transform: scale(0.95); }
        .btn-approve {
            background: #4CAF50;
            color: white;
            box-shadow: 0 4px 15px rgba(76, 175, 80, 0.4);
        }
        .btn-reject {
            background: #f44336;
            color: white;
            box-shadow: 0 4px 15px rgba(244, 67, 54, 0.4);
        }
        .btn-next {
            background: #2196F3;
            color: white;
            box-shadow: 0 4px 15px rgba(33, 150, 243, 0.4);
        }
        @media (max-width: 768px) {
            .buttons { 
                flex-direction: row; 
                gap: 0.8rem;
            }
            .btn { 
                padding: 1.5rem; 
                font-size: 1.4rem; 
            }
            .info-box {
                padding: 0.8rem;
            }
            .info-box h3 {
                font-size: 1.2rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <p style="text-align: center; font-size: 0.75rem; color: #666; margin-bottom: 1rem; padding: 0.5rem; background: #f5f5f5; border-radius: 8px;">
            <strong>Sağa kaydır / Sağ Ok = Onay ✅</strong> | <strong>Sola kaydır / Sol Ok = Red ❌</strong>
        </p>
        
        <div class="info-box" style="margin-bottom: 1rem;">
            <h3 id="patternText" style="margin-bottom: 0.5rem;">🤖 AI Pattern</h3>
            <p id="skuText" style="font-size: 0.85rem; margin: 0;">SKU Bilgileri</p>
        </div>
        
        <div class="buttons" style="margin-bottom: 1rem;">
            <button class="btn btn-reject" onclick="rejectPattern()">❌ RED</button>
            <button class="btn btn-approve" onclick="approvePattern()">✅ ONAY</button>
        </div>
        
        <div class="image-container" id="imageContainer" style="margin-bottom: 1rem;">
            <div class="swipe-indicator left" id="indicatorLeft">❌</div>
            <div class="swipe-indicator right" id="indicatorRight">✅</div>
            <img id="rugImage" class="rug-image" src="" alt="Halı Görseli" />
        </div>
        
        <button class="btn btn-next" onclick="nextPattern()" style="width: 100%; margin-bottom: 1rem;">⏭️ Sonraki</button>
        
        <div class="progress" id="progress">Yükleniyor...</div>
        
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #e0e0e0;">
            <div>
                <h2 style="margin: 0; font-size: 1.2rem; color: #333;">🎨 Pattern Kontrol Sistemi</h2>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 0.9rem; color: #666; margin-bottom: 0.3rem;">👤 {{ session.email }}</div>
                <div>
                    <a href="/results" style="color: #667eea; text-decoration: none; font-size: 0.9rem; margin-right: 1rem;">📊 Sonuçlarım</a>
                    <a href="/logout" style="color: #f44336; text-decoration: none; font-size: 0.9rem;">Çıkış</a>
                </div>
            </div>
        </div>
    </div>

    <script>
        let startX = 0, startY = 0, currentX = 0, isDragging = false;
        const threshold = 80;
        
        const imageEl = document.getElementById('rugImage');
        const indicatorLeft = document.getElementById('indicatorLeft');
        const indicatorRight = document.getElementById('indicatorRight');
        
        // Swipe events
        imageEl.addEventListener('touchstart', function(e) {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
            isDragging = true;
            console.log('👆 Touch start:', startX, startY);
        }, {passive: false});
        
        imageEl.addEventListener('touchmove', function(e) {
            if (!isDragging) return;
            currentX = e.touches[0].clientX;
            const deltaX = currentX - startX;
            const deltaY = Math.abs(e.touches[0].clientY - startY);
            
            if (Math.abs(deltaX) > deltaY && Math.abs(deltaX) > 20) {
                e.preventDefault();
                if (deltaX > 0) {
                    indicatorRight.classList.add('active');
                    indicatorLeft.classList.remove('active');
                } else {
                    indicatorLeft.classList.add('active');
                    indicatorRight.classList.remove('active');
                }
            }
        }, {passive: false});
        
        imageEl.addEventListener('touchend', function(e) {
            if (!isDragging) return;
            isDragging = false;
            const deltaX = currentX - startX;
            
            indicatorLeft.classList.remove('active');
            indicatorRight.classList.remove('active');
            
            console.log('👋 Touch end, deltaX:', deltaX);
            
            if (Math.abs(deltaX) > threshold) {
                if (deltaX > 0) {
                    approvePattern();
                } else {
                    rejectPattern();
                }
            }
        }, {passive: false});
        
        function loadPattern() {
            fetch('/api/current')
                .then(r => r.json())
                .then(data => {
                    if (data.error) {
                        document.getElementById('progress').textContent = data.error;
                        return;
                    }
                    document.getElementById('rugImage').src = data.image_url;
                    document.getElementById('patternText').textContent = '🤖 ' + data.ai_pattern;
                    document.getElementById('skuText').textContent = `Variant SKU: ${data.variant_sku} | Product SKU: ${data.product_sku}`;
                    document.getElementById('progress').textContent = `İlerleme: ${data.reviewed}/${data.total} tamamlandı | Kalan: ${data.remaining}`;
                });
        }
        
        function approvePattern() {
            fetch('/api/approve', {method: 'POST'})
                .then(() => loadPattern());
        }
        
        function rejectPattern() {
            fetch('/api/reject', {method: 'POST'})
                .then(() => loadPattern());
        }
        
        function nextPattern() {
            fetch('/api/next', {method: 'POST'})
                .then(() => loadPattern());
        }
        
        // Klavye kısayolları - Sağ ok = Onay, Sol ok = Red
        document.addEventListener('keydown', function(e) {
            // Sağ ok tuşu = Onay
            if (e.key === 'ArrowRight' || e.keyCode === 39) {
                e.preventDefault();
                console.log('➡️ Sağ ok tuşu - Onay');
                approvePattern();
            }
            // Sol ok tuşu = Red
            else if (e.key === 'ArrowLeft' || e.keyCode === 37) {
                e.preventDefault();
                console.log('⬅️ Sol ok tuşu - Red');
                rejectPattern();
            }
        });
        
        // İlk yükleme
        loadPattern();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    if 'email' not in session:
        return redirect(url_for('login'))
    return render_template_string(HTML_TEMPLATE, session=session)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        # Sadece @boutiquerugs.com uzantılı mailleri kabul et
        if not email.endswith('@boutiquerugs.com'):
            return render_template_string(LOGIN_TEMPLATE, error='❌ Sadece @boutiquerugs.com uzantılı email adresleri ile giriş yapabilirsiniz.')
        
        if '@' not in email or len(email) < 15:  # @boutiquerugs.com = 15 karakter
            return render_template_string(LOGIN_TEMPLATE, error='❌ Lütfen geçerli bir email adresi girin.')
        
        # Giriş başarılı
        session['email'] = email
        return redirect(url_for('index'))
    
    # GET request - login sayfasını göster
    if 'email' in session:
        return redirect(url_for('index'))
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    session.pop('email', None)
    return redirect(url_for('login'))

@app.route('/results')
def results():
    """Kullanıcının kendi sonuçlarını göster"""
    auth_error = require_auth()
    if auth_error:
        return redirect(url_for('login'))
    
    user_email = session.get('email', '')
    
    # Veritabanından kullanıcının kayıtlarını çek
    approved_data = []
    rejected_data = []
    
    if USE_DATABASE:
        try:
            db_session = SessionLocal()
            user_reviews = db_session.query(PatternReview).filter_by(reviewed_by=user_email).all()
            db_session.close()
            
            for review in user_reviews:
                item = {
                    'Variant SKU': review.variant_sku,
                    'Product SKU': review.product_sku,
                    'AI Detected Pattern': review.ai_pattern,
                    'Status': review.status,
                    'Timestamp': review.timestamp.isoformat() if review.timestamp else ''
                }
                if review.status == 'Approved':
                    approved_data.append(item)
                else:
                    rejected_data.append(item)
        except Exception as e:
            print(f"Veritabanı okuma hatası: {e}")
    else:
        # Fallback: CSV'den oku
        approved_file = DATA_DIR / "approved_patterns.csv"
        rejected_file = DATA_DIR / "rejected_patterns.csv"
        
        if approved_file.exists():
            try:
                approved_df = pd.read_csv(approved_file)
                if 'Reviewed By' in approved_df.columns:
                    user_approved = approved_df[approved_df['Reviewed By'] == user_email]
                    approved_data = user_approved.to_dict('records')
            except:
                pass
        
        if rejected_file.exists():
            try:
                rejected_df = pd.read_csv(rejected_file)
                if 'Reviewed By' in rejected_df.columns:
                    user_rejected = rejected_df[rejected_df['Reviewed By'] == user_email]
                    rejected_data = user_rejected.to_dict('records')
            except:
                pass
    
    results_html = f"""
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sonuçlarım - Pattern Kontrol Sistemi</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 1rem;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                padding: 2rem;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }}
            h1 {{ color: #333; margin-bottom: 1rem; }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 2rem;
            }}
            .btn {{
                padding: 0.8rem 1.5rem;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 10px;
                text-decoration: none;
                font-weight: bold;
                cursor: pointer;
            }}
            .stats {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 1rem;
                margin-bottom: 2rem;
            }}
            .stat-card {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 1.5rem;
                border-radius: 15px;
                text-align: center;
            }}
            .stat-card h3 {{
                font-size: 2rem;
                margin-bottom: 0.5rem;
            }}
            .stat-card p {{
                opacity: 0.9;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 1rem;
            }}
            th, td {{
                padding: 0.8rem;
                text-align: left;
                border-bottom: 1px solid #e0e0e0;
            }}
            th {{
                background: #f5f5f5;
                font-weight: bold;
            }}
            tr:hover {{
                background: #f9f9f9;
            }}
            .section {{
                margin-bottom: 3rem;
            }}
            .section h2 {{
                color: #333;
                margin-bottom: 1rem;
                padding-bottom: 0.5rem;
                border-bottom: 2px solid #667eea;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Sonuçlarım</h1>
                <div>
                    <a href="/" class="btn">← Ana Sayfa</a>
                    <a href="/admin/all" class="btn" style="background: #4CAF50; margin-left: 0.5rem;">📊 Tüm Kayıtlar</a>
                    <a href="/logout" class="btn" style="background: #f44336; margin-left: 0.5rem;">Çıkış</a>
                </div>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <h3>{len(approved_data)}</h3>
                    <p>✅ Onaylanan</p>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);">
                    <h3>{len(rejected_data)}</h3>
                    <p>❌ Reddedilen</p>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);">
                    <h3>{len(approved_data) + len(rejected_data)}</h3>
                    <p>📝 Toplam</p>
                </div>
            </div>
            
            <div class="section">
                <h2>✅ Onaylanan Pattern'ler ({len(approved_data)})</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Variant SKU</th>
                            <th>Product SKU</th>
                            <th>AI Pattern</th>
                            <th>Tarih</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    for item in approved_data:
        results_html += f"""
                        <tr>
                            <td>{item.get('Variant SKU', '')}</td>
                            <td>{item.get('Product SKU', '')}</td>
                            <td>{item.get('AI Detected Pattern', '')}</td>
                            <td>{item.get('Timestamp', '')[:19] if item.get('Timestamp') else ''}</td>
                        </tr>
        """
    
    results_html += """
                    </tbody>
                </table>
            </div>
            
            <div class="section">
                <h2>❌ Reddedilen Pattern'ler (""" + str(len(rejected_data)) + """)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Variant SKU</th>
                            <th>Product SKU</th>
                            <th>AI Pattern</th>
                            <th>Tarih</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    for item in rejected_data:
        results_html += f"""
                        <tr>
                            <td>{item.get('Variant SKU', '')}</td>
                            <td>{item.get('Product SKU', '')}</td>
                            <td>{item.get('AI Detected Pattern', '')}</td>
                            <td>{item.get('Timestamp', '')[:19] if item.get('Timestamp') else ''}</td>
                        </tr>
        """
    
    results_html += """
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """
    
    return results_html

def require_auth():
    """Authentication kontrolü"""
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    return None

@app.route('/api/current')
def api_current():
    auth_error = require_auth()
    if auth_error:
        return auth_error
    pattern = get_current_pattern()
    if pattern is None:
        return jsonify({'error': '🎉 Tüm pattern\'ler kontrol edildi!'})
    return jsonify(pattern)

@app.route('/api/approve', methods=['POST'])
def api_approve():
    auth_error = require_auth()
    if auth_error:
        return auth_error
    user_email = session.get('email', 'unknown')
    pattern = get_current_pattern()
    if pattern:
        save_review(pattern['variant_sku'], pattern['product_sku'], 
                   pattern['ai_pattern'], pattern['image_url'], approved=True)
        # Kullanıcı bazlı index'i artır
        current_index = session.get(f'current_index_{user_email}', 0)
        session[f'current_index_{user_email}'] = current_index + 1
    return jsonify({'success': True})

@app.route('/api/reject', methods=['POST'])
def api_reject():
    auth_error = require_auth()
    if auth_error:
        return auth_error
    user_email = session.get('email', 'unknown')
    pattern = get_current_pattern()
    if pattern:
        save_review(pattern['variant_sku'], pattern['product_sku'], 
                   pattern['ai_pattern'], pattern['image_url'], approved=False)
        # Kullanıcı bazlı index'i artır
        current_index = session.get(f'current_index_{user_email}', 0)
        session[f'current_index_{user_email}'] = current_index + 1
    return jsonify({'success': True})

@app.route('/api/next', methods=['POST'])
def api_next():
    auth_error = require_auth()
    if auth_error:
        return auth_error
    user_email = session.get('email', 'unknown')
    # Kullanıcı bazlı index'i artır
    current_index = session.get(f'current_index_{user_email}', 0)
    session[f'current_index_{user_email}'] = current_index + 1
    return jsonify({'success': True})

@app.route('/admin/all')
def admin_all():
    """Tüm kayıtları görüntüleme sayfası (tüm kullanıcılar)"""
    if 'email' not in session:
        return redirect(url_for('login'))
    
    # Veritabanından tüm kayıtları çek
    approved_data = []
    rejected_data = []
    user_stats = {}
    
    if USE_DATABASE:
        try:
            db_session = SessionLocal()
            all_reviews = db_session.query(PatternReview).all()
            db_session.close()
            
            for review in all_reviews:
                item = {
                    'Variant SKU': review.variant_sku,
                    'Product SKU': review.product_sku,
                    'AI Detected Pattern': review.ai_pattern,
                    'Reviewed By': review.reviewed_by,
                    'Status': review.status,
                    'Timestamp': review.timestamp.isoformat() if review.timestamp else ''
                }
                
                if review.status == 'Approved':
                    approved_data.append(item)
                else:
                    rejected_data.append(item)
                
                # İstatistikler
                email = review.reviewed_by
                if email not in user_stats:
                    user_stats[email] = {'approved': 0, 'rejected': 0}
                if review.status == 'Approved':
                    user_stats[email]['approved'] += 1
                else:
                    user_stats[email]['rejected'] += 1
        except Exception as e:
            print(f"Veritabanı okuma hatası: {e}")
    else:
        # Fallback: CSV'den oku
        approved_file = DATA_DIR / "approved_patterns.csv"
        rejected_file = DATA_DIR / "rejected_patterns.csv"
        
        if approved_file.exists():
            try:
                df_approved = pd.read_csv(approved_file, encoding='utf-8-sig', on_bad_lines='skip')
                approved_data = df_approved.to_dict('records')
            except Exception as e:
                print(f"Approved CSV okuma hatası: {e}")
        
        if rejected_file.exists():
            try:
                df_rejected = pd.read_csv(rejected_file, encoding='utf-8-sig', on_bad_lines='skip')
                rejected_data = df_rejected.to_dict('records')
            except Exception as e:
                print(f"Rejected CSV okuma hatası: {e}")
        
        # Kullanıcı bazlı istatistikler
        for item in approved_data + rejected_data:
            email = item.get('Reviewed By', 'unknown')
            if email not in user_stats:
                user_stats[email] = {'approved': 0, 'rejected': 0}
            if item.get('Status') == 'Approved':
                user_stats[email]['approved'] += 1
            else:
                user_stats[email]['rejected'] += 1
    
    admin_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>📊 Tüm Kayıtlar - Admin</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                margin: 0;
                padding: 1rem;
            }}
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                padding: 2rem;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 2rem;
                flex-wrap: wrap;
                gap: 1rem;
            }}
            h1 {{ color: #333; margin: 0; }}
            .btn {{
                padding: 0.8rem 1.5rem;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 10px;
                text-decoration: none;
                font-weight: bold;
                cursor: pointer;
                display: inline-block;
            }}
            .btn-danger {{
                background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
            }}
            .stats {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 1rem;
                margin-bottom: 2rem;
            }}
            .stat-card {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 1.5rem;
                border-radius: 15px;
                text-align: center;
            }}
            .stat-card h3 {{
                font-size: 2.5rem;
                margin: 0;
            }}
            .stat-card p {{
                margin: 0.5rem 0 0 0;
                font-size: 1.1rem;
            }}
            .user-stats {{
                background: #f5f5f5;
                padding: 1.5rem;
                border-radius: 15px;
                margin-bottom: 2rem;
            }}
            .user-stats h2 {{
                margin-top: 0;
                color: #333;
            }}
            .user-item {{
                display: flex;
                justify-content: space-between;
                padding: 0.8rem;
                margin: 0.5rem 0;
                background: white;
                border-radius: 10px;
                border-left: 4px solid #667eea;
            }}
            .section {{
                margin-bottom: 3rem;
            }}
            .section h2 {{
                color: #333;
                margin-bottom: 1rem;
                padding-bottom: 0.5rem;
                border-bottom: 2px solid #667eea;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 1rem;
            }}
            th, td {{
                padding: 1rem;
                text-align: left;
                border-bottom: 1px solid #e0e0e0;
            }}
            th {{
                background: #f5f5f5;
                font-weight: bold;
                color: #333;
            }}
            tr:hover {{
                background: #f9f9f9;
            }}
            .download-btn {{
                background: #4CAF50;
                margin-left: 0.5rem;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Tüm Kayıtlar (Admin)</h1>
                <div>
                    <a href="/" class="btn">← Ana Sayfa</a>
                    <a href="/results" class="btn">📊 Sonuçlarım</a>
                    <a href="/logout" class="btn btn-danger">Çıkış</a>
                </div>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <h3>{len(approved_data)}</h3>
                    <p>✅ Toplam Onaylanan</p>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);">
                    <h3>{len(rejected_data)}</h3>
                    <p>❌ Toplam Reddedilen</p>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);">
                    <h3>{len(approved_data) + len(rejected_data)}</h3>
                    <p>📝 Toplam Kayıt</p>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #4CAF50 0%, #388E3C 100%);">
                    <h3>{len(user_stats)}</h3>
                    <p>👥 Kullanıcı Sayısı</p>
                </div>
            </div>
            
            <div class="user-stats">
                <h2>👥 Kullanıcı İstatistikleri</h2>
    """
    
    for email, stats in sorted(user_stats.items(), key=lambda x: x[1]['approved'] + x[1]['rejected'], reverse=True):
        admin_html += f"""
                <div class="user-item">
                    <div>
                        <strong>{email}</strong>
                        <div style="font-size: 0.9rem; color: #666; margin-top: 0.3rem;">
                            ✅ {stats['approved']} Onay | ❌ {stats['rejected']} Red | 📝 {stats['approved'] + stats['rejected']} Toplam
                        </div>
                    </div>
                </div>
        """
    
    admin_html += """
            </div>
            
            <div class="section">
                <h2>✅ Tüm Onaylanan Pattern'ler (""" + str(len(approved_data)) + """) 
                    <a href="/download/approved" class="btn download-btn">📥 CSV İndir</a>
                </h2>
                <table>
                    <thead>
                        <tr>
                            <th>Variant SKU</th>
                            <th>Product SKU</th>
                            <th>AI Pattern</th>
                            <th>Reviewed By</th>
                            <th>Tarih</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    for item in approved_data:
        admin_html += f"""
                        <tr>
                            <td>{item.get('Variant SKU', '')}</td>
                            <td>{item.get('Product SKU', '')}</td>
                            <td>{item.get('AI Detected Pattern', '')}</td>
                            <td>{item.get('Reviewed By', '')}</td>
                            <td>{item.get('Timestamp', '')[:19] if item.get('Timestamp') else ''}</td>
                        </tr>
        """
    
    admin_html += """
                    </tbody>
                </table>
            </div>
            
            <div class="section">
                <h2>❌ Tüm Reddedilen Pattern'ler (""" + str(len(rejected_data)) + """) 
                    <a href="/download/rejected" class="btn download-btn">📥 CSV İndir</a>
                </h2>
                <table>
                    <thead>
                        <tr>
                            <th>Variant SKU</th>
                            <th>Product SKU</th>
                            <th>AI Pattern</th>
                            <th>Reviewed By</th>
                            <th>Tarih</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    for item in rejected_data:
        admin_html += f"""
                        <tr>
                            <td>{item.get('Variant SKU', '')}</td>
                            <td>{item.get('Product SKU', '')}</td>
                            <td>{item.get('AI Detected Pattern', '')}</td>
                            <td>{item.get('Reviewed By', '')}</td>
                            <td>{item.get('Timestamp', '')[:19] if item.get('Timestamp') else ''}</td>
                        </tr>
        """
    
    admin_html += """
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """
    
    return admin_html

@app.route('/download/<file_type>')
def download_csv(file_type):
    """CSV dosyalarını indirme endpoint'i (veritabanından)"""
    if 'email' not in session:
        return redirect(url_for('login'))
    
    try:
        if USE_DATABASE:
            db_session = SessionLocal()
            if file_type == 'approved':
                reviews = db_session.query(PatternReview).filter_by(status='Approved').all()
                filename = 'approved_patterns.csv'
            elif file_type == 'rejected':
                reviews = db_session.query(PatternReview).filter_by(status='Rejected').all()
                filename = 'rejected_patterns.csv'
            else:
                return jsonify({'error': 'Invalid file type'}), 400
            
            db_session.close()
            
            # DataFrame oluştur
            data = []
            for review in reviews:
                data.append({
                    'Variant SKU': review.variant_sku,
                    'Product SKU': review.product_sku,
                    'AI Detected Pattern': review.ai_pattern,
                    'Design Image URL': review.image_url,
                    'Status': review.status,
                    'Reviewed By': review.reviewed_by,
                    'Timestamp': review.timestamp.isoformat() if review.timestamp else ''
                })
            
            df = pd.DataFrame(data)
            
            # CSV'yi memory'de oluştur
            output = io.StringIO()
            df.to_csv(output, index=False, encoding='utf-8-sig')
            output.seek(0)
            
            return send_file(
                io.BytesIO(output.getvalue().encode('utf-8-sig')),
                mimetype='text/csv',
                as_attachment=True,
                download_name=filename
            )
        else:
            # Fallback: CSV dosyasından
            if file_type == 'approved':
                file_path = DATA_DIR / "approved_patterns.csv"
                filename = 'approved_patterns.csv'
            elif file_type == 'rejected':
                file_path = DATA_DIR / "rejected_patterns.csv"
                filename = 'rejected_patterns.csv'
            else:
                return jsonify({'error': 'Invalid file type'}), 400
            
            if not file_path.exists():
                return jsonify({'error': 'File not found'}), 404
            
            return send_file(
                str(file_path),
                mimetype='text/csv',
                as_attachment=True,
                download_name=filename
            )
    except Exception as e:
        print(f"CSV indirme hatası: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
