import streamlit as st
import pandas as pd
import os
from datetime import datetime
from pathlib import Path
import hashlib
import time

# Sayfa yapılandırması
st.set_page_config(
    page_title="Pattern Kontrol Sistemi",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS - Mobil uyumlu swipe benzeri butonlar
st.markdown("""
<style>
    .main {
        padding: 0.5rem;
    }
    
    .pattern-card {
        background: white;
        border-radius: 15px;
        padding: 0;
        margin: 0.2rem 0 !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
    }
    
    .rug-image {
        max-width: 100%;
        max-height: 400px;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    
    .pattern-info {
        font-size: 1.1rem;
        margin: 0.5rem 0;
        padding: 1rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    
    .pattern-info strong {
        color: #fff;
        font-weight: 600;
    }
    
    .swipeable-card {
        position: relative;
        touch-action: pan-y;
        user-select: none;
        -webkit-user-select: none;
    }
    
    .swipe-hint {
        text-align: center;
        margin: 0.3rem 0;
        color: #666;
        font-size: 0.85rem;
        padding: 0.3rem;
    }
    
    .swipe-indicator {
        position: absolute;
        top: 50%;
        transform: translateY(-50%);
        font-size: 3rem;
        opacity: 0;
        transition: opacity 0.3s, transform 0.3s;
        pointer-events: none;
        z-index: 10;
    }
    
    .swipe-indicator.left {
        left: 20px;
        color: #f44336;
    }
    
    .swipe-indicator.right {
        right: 20px;
        color: #4CAF50;
    }
    
    .swipe-indicator.active {
        opacity: 0.8;
        transform: translateY(-50%) scale(1.2);
    }
    
    .action-buttons {
        display: flex;
        gap: 1rem;
        justify-content: center;
        margin-top: 2rem;
    }
    
    /* Büyük butonlar için genel stil */
    .stButton > button {
        padding: 1rem 2rem !important;
        font-size: 1.3rem !important;
        font-weight: bold !important;
        border-radius: 50px !important;
        min-height: 60px !important;
        transition: all 0.3s !important;
        margin: 0.3rem 0 !important;
    }
    
    /* Onay butonu - Yeşil */
    .btn-approve-custom,
    .stButton > button.btn-approve-custom {
        background: #4CAF50 !important;
        color: white !important;
        box-shadow: 0 4px 15px rgba(76, 175, 80, 0.4) !important;
    }
    
    .btn-approve-custom:hover,
    .stButton > button.btn-approve-custom:hover {
        background: #45a049 !important;
        transform: scale(1.05) !important;
    }
    
    /* Red butonu - Kırmızı */
    .btn-reject-custom,
    .stButton > button.btn-reject-custom {
        background: #f44336 !important;
        color: white !important;
        box-shadow: 0 4px 15px rgba(244, 67, 54, 0.4) !important;
    }
    
    .btn-reject-custom:hover,
    .stButton > button.btn-reject-custom:hover {
        background: #da190b !important;
        transform: scale(1.05) !important;
    }
    
    .progress-info {
        text-align: center;
        font-size: 1rem;
        margin: 0.5rem 0;
        padding: 0.7rem;
        background: #e3f2fd;
        border-radius: 8px;
    }
    
    @media (max-width: 768px) {
        .action-buttons {
            flex-direction: column;
        }
        
        .stButton > button {
            width: 100% !important;
            padding: 2rem !important;
            font-size: 1.8rem !important;
            min-height: 80px !important;
        }
        
        .pattern-info {
            font-size: 1rem;
            padding: 1rem;
        }
        
        .pattern-info div {
            font-size: 1.5rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# Dosya yolları - Hem localhost hem Streamlit Cloud için
# app.py web_app/ klasöründe, data/ klasörü bir üst dizinde
BASE_DIR = Path(__file__).parent.parent  # yakup/ klasörü
DATA_DIR = BASE_DIR / "data"

# Alternatif yollar kontrolü (eğer dosya bulunamazsa)
import os
PATTERNS_FILE = DATA_DIR / "test_ai_pattern_results.csv"
if not PATTERNS_FILE.exists():
    # Mevcut çalışma dizininde ara
    current_dir = Path(os.getcwd())
    if (current_dir / "data" / "test_ai_pattern_results.csv").exists():
        DATA_DIR = current_dir / "data"
    elif (current_dir.parent / "data" / "test_ai_pattern_results.csv").exists():
        DATA_DIR = current_dir.parent / "data"
    PATTERNS_FILE = DATA_DIR / "test_ai_pattern_results.csv"

APPROVED_FILE = DATA_DIR / "approved_patterns.csv"
REJECTED_FILE = DATA_DIR / "rejected_patterns.csv"

# Session state başlatma
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'patterns_data' not in st.session_state:
    st.session_state.patterns_data = None
if 'reviewed_skus' not in st.session_state:
    st.session_state.reviewed_skus = set()

def load_patterns():
    """Pattern verilerini yükle"""
    if not PATTERNS_FILE.exists():
        st.error(f"Pattern dosyası bulunamadı: {PATTERNS_FILE}")
        return None
    
    try:
        # CSV'yi daha esnek okuma - hatalı satırları atla veya düzelt
        read_params = {
            'encoding': 'utf-8-sig',  # UTF-8 BOM desteği
            'quotechar': '"',  # Tırnak işareti ile sarmalanmış alanlar
            'skipinitialspace': True,  # Başlangıç boşluklarını atla
            'low_memory': False  # Daha iyi tip çıkarımı
        }
        
        # Pandas versiyonuna göre hatalı satır parametresi
        try:
            df = pd.read_csv(PATTERNS_FILE, on_bad_lines='skip', **read_params)
        except TypeError:
            # Eski pandas versiyonu için
            try:
                df = pd.read_csv(PATTERNS_FILE, error_bad_lines=False, warn_bad_lines=False, **read_params)
            except TypeError:
                # En eski versiyon için
                df = pd.read_csv(PATTERNS_FILE, **read_params)
        
        # Eğer sütun sayısı beklenenden fazlaysa, fazla sütunları birleştir
        expected_columns = ['Variant SKU', 'Product SKU', 'Original Patterns', 'AI Detected Pattern', 'Design Image URL']
        if len(df.columns) > len(expected_columns):
            # Fazla sütunları "AI Detected Pattern" sütununa birleştir
            if 'AI Detected Pattern' in df.columns:
                extra_cols = df.columns[len(expected_columns):]
                for col in extra_cols:
                    df['AI Detected Pattern'] = df['AI Detected Pattern'].astype(str) + ', ' + df[col].astype(str)
                df = df[expected_columns]
        
        # Sütun isimlerini düzelt
        if len(df.columns) >= len(expected_columns):
            df.columns = expected_columns[:len(df.columns)]
        
        # Boş değerleri temizle
        df = df.dropna(subset=['Variant SKU', 'Design Image URL'])
        
        # "AI Detected Pattern" sütunundaki ekstra bilgileri temizle (örn: "Abstract,3/3" -> "Abstract")
        if 'AI Detected Pattern' in df.columns:
            df['AI Detected Pattern'] = df['AI Detected Pattern'].astype(str).apply(
                lambda x: x.split(',')[0].strip() if ',' in x and any(char.isdigit() for char in x.split(',')[1] if len(x.split(',')) > 1) else x.strip()
            )
            # Uzun açıklamaları temizle (sadece pattern adını al)
            pattern_names = ['Geometric', 'Floral', 'Striped', 'Solid', 'Abstract', 'Medallion', 
                           'Tribal', 'Chevron', 'Paisley', 'Damask', 'Ikat', 'Herringbone', 
                           'Plaid', 'Checkered', 'Polka Dot', 'Animal Print', 'Zebra Print', 
                           'Oriental', 'Persian', 'Moroccan', 'Unknown', 'Error']
            def extract_pattern(text):
                text_str = str(text)
                # Önce pattern adlarını ara
                for pattern in pattern_names:
                    if pattern.lower() in text_str.lower():
                        return pattern
                # Eğer bulunamazsa, ilk kelimeyi al (uzun açıklamalardan kurtul)
                if len(text_str) > 30:
                    words = text_str.split()
                    for word in words:
                        if word.capitalize() in pattern_names:
                            return word.capitalize()
                    return text_str.split()[0] if words else "Unknown"
                return text_str.strip()
            
            df['AI Detected Pattern'] = df['AI Detected Pattern'].apply(extract_pattern)
        
        return df
    except Exception as e:
        st.error(f"Dosya okuma hatası: {e}")
        import traceback
        st.code(traceback.format_exc())
        return None

def load_reviewed_skus():
    """Onaylanmış/reddedilmiş SKU'ları yükle"""
    reviewed = set()
    
    # Onaylananları yükle
    if APPROVED_FILE.exists():
        try:
            approved_df = pd.read_csv(APPROVED_FILE)
            if 'Variant SKU' in approved_df.columns:
                reviewed.update(approved_df['Variant SKU'].dropna().astype(str))
        except:
            pass
    
    # Reddedilenleri yükle
    if REJECTED_FILE.exists():
        try:
            rejected_df = pd.read_csv(REJECTED_FILE)
            if 'Variant SKU' in rejected_df.columns:
                reviewed.update(rejected_df['Variant SKU'].dropna().astype(str))
        except:
            pass
    
    return reviewed

def save_review(variant_sku, product_sku, ai_pattern, image_url, approved=True):
    """Onay/Red kaydını kaydet"""
    timestamp = datetime.now().isoformat()
    user_email = st.session_state.user_email or "unknown"
    
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
    
    # Dosya yoksa oluştur, varsa ekle
    if filename.exists():
        df.to_csv(filename, mode='a', header=False, index=False, encoding='utf-8-sig')
    else:
        df.to_csv(filename, index=False, encoding='utf-8-sig')
    
    # Session state'e ekle
    st.session_state.reviewed_skus.add(str(variant_sku))

def authenticate():
    """Email ile basit authentication"""
    st.title("🔐 Giriş")
    st.markdown("---")
    
    email = st.text_input("Email adresinizi girin:", placeholder="ornek@email.com")
    
    if st.button("Giriş Yap", type="primary", use_container_width=True):
        if email and "@" in email:
            st.session_state.authenticated = True
            st.session_state.user_email = email
            st.rerun()
        else:
            st.error("Lütfen geçerli bir email adresi girin.")

def main_app():
    """Ana uygulama"""
    # Pattern verilerini yükle
    if st.session_state.patterns_data is None:
        with st.spinner("Veriler yükleniyor..."):
            st.session_state.patterns_data = load_patterns()
            st.session_state.reviewed_skus = load_reviewed_skus()
    
    if st.session_state.patterns_data is None:
        st.error("Veriler yüklenemedi. Lütfen dosya yollarını kontrol edin.")
        return
    
    # Kullanıcı bilgisi
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### 🎨 Pattern Kontrol Sistemi")
    with col2:
        if st.button("Çıkış", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user_email = None
            st.rerun()
        st.caption(f"👤 {st.session_state.user_email}")
    
    st.markdown("---")
    
    # Filtrele: Sadece kontrol edilmemiş pattern'ler
    df = st.session_state.patterns_data.copy()
    df = df[~df['Variant SKU'].astype(str).isin(st.session_state.reviewed_skus)]
    
    if len(df) == 0:
        st.success("🎉 Tüm pattern'ler kontrol edildi!")
        st.balloons()
        return
    
    # İlerleme bilgisi
    total = len(st.session_state.patterns_data)
    reviewed = len(st.session_state.reviewed_skus)
    remaining = len(df)
    
    st.markdown(f"""
    <div class="progress-info">
        <strong>İlerleme:</strong> {reviewed}/{total} tamamlandı | <strong>Kalan:</strong> {remaining}
    </div>
    """, unsafe_allow_html=True)
    
    # Mevcut pattern'i göster
    if st.session_state.current_index >= len(df):
        st.session_state.current_index = 0
    
    current_row = df.iloc[st.session_state.current_index]
    variant_sku = current_row['Variant SKU']
    product_sku = current_row['Product SKU']
    ai_pattern = current_row['AI Detected Pattern']
    image_url = current_row['Design Image URL']
    
    # Pattern kartı - Swipe özellikli
    st.markdown(f'''
    <div class="pattern-card swipeable-card" id="swipeCard" 
         data-variant-sku="{variant_sku}" 
         data-product-sku="{product_sku}" 
         data-ai-pattern="{ai_pattern}" 
         data-image-url="{image_url}">
        <div class="swipe-indicator left">❌</div>
        <div class="swipe-indicator right">✅</div>
    </div>
    ''', unsafe_allow_html=True)
    
    # Pattern bilgisi - Görselin ÜSTÜNDE
    st.markdown(f"""
    <div class="pattern-info">
        <div style="text-align: center;">
            <div style="font-size: 1.5rem; margin-bottom: 0.3rem;">🤖 {ai_pattern}</div>
            <div style="font-size: 0.9rem; opacity: 0.9;">
                <strong>Variant SKU:</strong> {variant_sku} | 
                <strong>Product SKU:</strong> {product_sku}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Onay/Red butonları - ÜSTTE, görselden önce
    # Butonlara özel ID'ler ekleyerek JavaScript'ten erişimi kolaylaştır
    col1, col2 = st.columns(2)
    
    with col1:
        reject_clicked = st.button("❌ RED", type="primary", use_container_width=True, 
                    help="Bu pattern'i reddet (veya Sol ok tuşu)", key=f"reject_{variant_sku}")
        if reject_clicked:
            save_review(variant_sku, product_sku, ai_pattern, image_url, approved=False)
            st.session_state.current_index += 1
            st.rerun()
    
    with col2:
        approve_clicked = st.button("✅ ONAY", type="primary", use_container_width=True,
                    help="Bu pattern'i onayla (veya Sağ ok tuşu)", key=f"approve_{variant_sku}")
        if approve_clicked:
            save_review(variant_sku, product_sku, ai_pattern, image_url, approved=True)
            st.session_state.current_index += 1
            st.rerun()
    
    # Butonlara ID ekle (JavaScript için)
    st.markdown(f"""
    <script>
    setTimeout(function() {{
        const buttons = document.querySelectorAll('button');
        buttons.forEach(btn => {{
            const text = (btn.textContent || btn.innerText || '').trim();
            if (text.includes('RED') || text.includes('❌')) {{
                btn.id = 'reject-button-{variant_sku}';
                btn.setAttribute('data-action', 'reject');
            }} else if (text.includes('ONAY') || text.includes('✅')) {{
                btn.id = 'approve-button-{variant_sku}';
                btn.setAttribute('data-action', 'approve');
            }}
        }});
    }}, 200);
    </script>
    """, unsafe_allow_html=True)
    
    # Swipe talimatı
    st.markdown("""
    <div class="swipe-hint">
        💡 <strong>Mobil:</strong> Görsele dokunup sağa kaydır = Onay ✅ | Sola kaydır = Red ❌<br>
        💡 <strong>Masaüstü:</strong> Büyük butonları kullanın
    </div>
    """, unsafe_allow_html=True)
    
    # Görsel - Boşluksuz
    try:
        st.image(image_url, use_container_width=True)
    except:
        st.error(f"Görsel yüklenemedi: {image_url}")
    
    # JavaScript - Butonlara class ekle ve swipe desteği
    button_style_js = """
    <script>
    setTimeout(function() {
        const buttons = document.querySelectorAll('.stButton > button');
        buttons.forEach(btn => {
            const text = btn.textContent || btn.innerText;
            if (text.includes('ONAY') || text.includes('✅')) {
                btn.classList.add('btn-approve-custom');
            } else if (text.includes('RED') || text.includes('❌')) {
                btn.classList.add('btn-reject-custom');
            }
        });
    }, 100);
    </script>
    """
    st.markdown(button_style_js, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # JavaScript - Swipe ve klavye desteği
    swipe_js = f"""
    <script>
    console.log('Pattern Kontrol - JavaScript yüklendi');
    (function() {{
        let startX = 0, startY = 0, currentX = 0, isDragging = false;
        const threshold = 80;
        
        // Touch events (mobil swipe)
        document.addEventListener('touchstart', function(e) {{
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
            isDragging = true;
        }}, {{passive: false}});
        
        document.addEventListener('touchmove', function(e) {{
            if (!isDragging) return;
            currentX = e.touches[0].clientX;
            const deltaX = currentX - startX;
            const deltaY = Math.abs(e.touches[0].clientY - startY);
            
            if (Math.abs(deltaX) > deltaY && Math.abs(deltaX) > 20) {{
                e.preventDefault();
                const card = document.querySelector('.swipeable-card');
                if (card) {{
                    const indicator = deltaX > 0 ? 
                        card.querySelector('.swipe-indicator.right') : 
                        card.querySelector('.swipe-indicator.left');
                    if (indicator) {{
                        indicator.classList.add('active');
                        indicator.style.opacity = Math.min(Math.abs(deltaX) / threshold, 0.8);
                    }}
                }}
            }}
        }}, {{passive: false}});
        
        document.addEventListener('touchend', function(e) {{
            if (!isDragging) return;
            isDragging = false;
            const deltaX = currentX - startX;
            
            document.querySelectorAll('.swipe-indicator').forEach(ind => {{
                ind.classList.remove('active');
                ind.style.opacity = '0';
            }});
            
            if (Math.abs(deltaX) > threshold) {{
                const buttons = Array.from(document.querySelectorAll('button'));
                if (deltaX > 0) {{
                    // Sağa swipe - Onay
                    const approveBtn = buttons.find(b => {{
                        const text = (b.textContent || b.innerText || '').trim();
                        return text.includes('ONAY') || text.includes('✅');
                    }});
                    if (approveBtn) approveBtn.click();
                }} else {{
                    // Sola swipe - Red
                    const rejectBtn = buttons.find(b => {{
                        const text = (b.textContent || b.innerText || '').trim();
                        return text.includes('RED') || text.includes('❌');
                    }});
                    if (rejectBtn) rejectBtn.click();
                }}
            }}
        }});
        
        // Klavye kısayolları kaldırıldı - Streamlit iframe yapısı nedeniyle çalışmıyor
        // Sadece swipe özelliği aktif
        console.log('✅ Swipe özelliği aktif: Sağa kaydır = Onay, Sola kaydır = Red');
    }})();
    </script>
    """
    st.markdown(swipe_js, unsafe_allow_html=True)
    
    # JavaScript çalışıyor mu kontrol et
    st.markdown("""
    <script>
    // JavaScript çalışıyor mu test et
    if (typeof console !== 'undefined') {
        console.log('✅ JavaScript aktif');
    }
    </script>
    """, unsafe_allow_html=True)
    
    # Navigasyon
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("⏭️ Sonraki", use_container_width=True):
            st.session_state.current_index += 1
            if st.session_state.current_index >= len(df):
                st.session_state.current_index = 0
            st.rerun()

# Ana akış
if not st.session_state.authenticated:
    authenticate()
else:
    main_app()
