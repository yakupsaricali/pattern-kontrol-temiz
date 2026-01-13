from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
import pandas as pd
from pathlib import Path
from datetime import datetime
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Session için secret key

# Dosya yolları
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

PATTERNS_FILE = DATA_DIR / "test_ai_pattern_results.csv"
APPROVED_FILE = DATA_DIR / "approved_patterns.csv"
REJECTED_FILE = DATA_DIR / "rejected_patterns.csv"

# Global state
patterns_data = None
reviewed_skus = set()
current_index = 0

def load_patterns():
    global patterns_data
    if not PATTERNS_FILE.exists():
        return None
    
    try:
        df = pd.read_csv(PATTERNS_FILE, encoding='utf-8-sig', on_bad_lines='skip', low_memory=False)
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
        return df
    except Exception as e:
        print(f"Hata: {e}")
        return None

def load_reviewed_skus():
    global reviewed_skus
    reviewed = set()
    if APPROVED_FILE.exists():
        try:
            approved_df = pd.read_csv(APPROVED_FILE)
            if 'Variant SKU' in approved_df.columns:
                reviewed.update(approved_df['Variant SKU'].dropna().astype(str))
        except:
            pass
    if REJECTED_FILE.exists():
        try:
            rejected_df = pd.read_csv(REJECTED_FILE)
            if 'Variant SKU' in rejected_df.columns:
                reviewed.update(rejected_df['Variant SKU'].dropna().astype(str))
        except:
            pass
    reviewed_skus = reviewed
    return reviewed

def get_current_pattern():
    global patterns_data, reviewed_skus, current_index
    if patterns_data is None:
        load_patterns()
        load_reviewed_skus()
    if patterns_data is None or len(patterns_data) == 0:
        return None
    # Filtrele: Hem reviewed olanları hem de "Error" pattern'lerini atla
    df = patterns_data[
        ~patterns_data['Variant SKU'].astype(str).isin(reviewed_skus) &
        (patterns_data['AI Detected Pattern'].astype(str).str.strip().str.upper() != 'ERROR')
    ].copy()
    if len(df) == 0:
        return None
    if current_index >= len(df):
        current_index = 0
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
    timestamp = datetime.now().isoformat()
    user_email = session.get('email', 'unknown')
    data = {
        'Variant SKU': variant_sku,
        'Product SKU': product_sku,
        'AI Detected Pattern': ai_pattern,
        'Design Image URL': image_url,
        'Status': 'Approved' if approved else 'Rejected',
        'Reviewed By': user_email,
        'Timestamp': timestamp
    }
    filename = APPROVED_FILE if approved else REJECTED_FILE
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
    
    # Onaylanan ve reddedilen sonuçları yükle
    approved_data = []
    rejected_data = []
    
    if APPROVED_FILE.exists():
        try:
            approved_df = pd.read_csv(APPROVED_FILE)
            if 'Reviewed By' in approved_df.columns:
                user_approved = approved_df[approved_df['Reviewed By'] == user_email]
                approved_data = user_approved.to_dict('records')
        except:
            pass
    
    if REJECTED_FILE.exists():
        try:
            rejected_df = pd.read_csv(REJECTED_FILE)
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
    global current_index
    pattern = get_current_pattern()
    if pattern:
        save_review(pattern['variant_sku'], pattern['product_sku'], 
                   pattern['ai_pattern'], pattern['image_url'], approved=True)
        current_index += 1
    return jsonify({'success': True})

@app.route('/api/reject', methods=['POST'])
def api_reject():
    auth_error = require_auth()
    if auth_error:
        return auth_error
    global current_index
    pattern = get_current_pattern()
    if pattern:
        save_review(pattern['variant_sku'], pattern['product_sku'], 
                   pattern['ai_pattern'], pattern['image_url'], approved=False)
        current_index += 1
    return jsonify({'success': True})

@app.route('/api/next', methods=['POST'])
def api_next():
    auth_error = require_auth()
    if auth_error:
        return auth_error
    global current_index
    current_index += 1
    return jsonify({'success': True})

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
