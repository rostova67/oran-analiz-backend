import pandas as pd
from sqlalchemy import create_engine, text
import requests
import datetime
import time

print("=" * 60)
print("⚡ HIZLI SUPABASE YÜKLEMESİ VE TELEGRAM BİLDİRİMİ BAŞLIYOR")
print("=" * 60)

# ============================================================
# VERİTABANI BAĞLANTISI (SUPABASE)
# ============================================================
DB_URL = "postgresql://postgres:KatarinaRostova67@db.xqhdhwdgitksemfidsdi.supabase.co:5432/postgres?sslmode=require"

engine = create_engine(
    DB_URL,
    pool_pre_ping=True,
    connect_args={
        "connect_timeout": 60
    }
)

# ============================================================
# YENİ TELEGRAM BOT VE CHAT ID AYARLARI
# ============================================================
TELEGRAM_BOT_TOKEN = "8455605085:AAE69B-01Qb_atFOYMJOjepEpIgLFiJ5Jdk"

TELEGRAM_CHAT_IDS = [
    "8464565138",    # Senin Chat ID'n
    "7322987114"     # Arkadaşının Chat ID'si
]

BACKEND_URL = "https://oran-analiz-backend.onrender.com"


def send_telegram_message(message: str):
    """Tanımlı tüm Chat ID'lerine Telegram mesajı gönderir."""
    if not TELEGRAM_BOT_TOKEN:
        print("⚠️ Telegram Bot Token eksik, mesaj gönderimi atlanıyor.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    for chat_id in TELEGRAM_CHAT_IDS:
        if not chat_id:
            continue
        try:
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            res = requests.post(url, json=payload, timeout=10)
            if res.status_code == 200:
                print(f"✅ Telegram mesajı gönderildi -> Chat ID: {chat_id}")
            elif "chat not found" in res.text:
                print(f"⚠️ Telegram Hatası ({chat_id}): Kullanıcı bota henüz /start dememiş!")
            else:
                print(f"⚠️ Telegram gönderim hatası ({chat_id}): {res.text}")
        except Exception as e:
            print(f"❌ Telegram isteği başarısız ({chat_id}): {e}")


def get_first_valid(item, keys, default=""):
    """Sözlükteki olası anahtar kelimelerden ilk dolu olanı döndürür."""
    for k in keys:
        val = item.get(k)
        if val is not None and val != "":
            return val
    return default


def format_match_line(idx, item, perc_key):
    """Saat tekrarı olmadan temiz biçimlendirme üretir."""
    saat = get_first_valid(item, ["SAAT", "TIME", "time", "hour"], "--:--")
    mac = get_first_valid(item, ["MAC", "MATCH", "match", "teams"], "Bilinmeyen Maç")
    
    yuzde = float(get_first_valid(item, [perc_key, perc_key.lower(), "YUZDE", "perc"], 0.0))
    ornek = get_first_valid(item, ["SAMPLE", "ORNEK", "sample", "count", "TOPLAM_MAC"], 0)
    
    skor = get_first_valid(item, [
        "EN_OLASI_SKOR", "TOP_SKOR", "SKOR", "SCORE", "most_common_score", 
        "MOST_COMMON_SCORE", "skor", "score"
    ], "2-1")
    
    skor_yuzde = float(get_first_valid(item, [
        "SKOR_YUZDE", "SCORE_PERC", "SKOR_YUZDESI", "most_common_score_perc",
        "MOST_COMMON_SCORE_PERC", "skor_yuzde", "score_perc"
    ], 30.0))

    return (
        f"{idx}. [{saat}] <b>{mac}</b>\n"
        f"    └ 🔥 <b>%{yuzde:.1f}</b> | 👥 <b>{ornek} örnek</b> | 🎯 Skor: <code>{skor}</code> (<b>%{skor_yuzde:.1f}</b>)\n"
    )


def generate_and_send_bugunun_enleri():
    """Backend API'den canlı verileri çekip 7 ayrı detaylı mesaj olarak hazırlar ve yollar."""
    print("\n📊 Bugünün Enleri analizi çekiliyor...")
    try:
        timestamp = int(time.time())
        api_url = f"{BACKEND_URL}/api/bugunun-enleri?_t={timestamp}"
        
        headers = {'Cache-Control': 'no-cache, no-store, must-revalidate', 'Pragma': 'no-cache'}
        response = requests.get(api_url, headers=headers, timeout=20)

        if response.status_code != 200:
            print(f"⚠️️ Bugünün Enleri API'sinden veri alınamadı (Status: {response.status_code}).")
            return

        data = response.json()
        now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        min_mac = data.get("min_mac", 7)
        tolerans = data.get("tolerans", 0.05)

        categories = [
            ("ms1", "🏆 MS 1 EN YÜKSEKLER", "MS1_YUZDE"),
            ("ms2", "🔴 MS 2 EN YÜKSEKLER", "MS2_YUZDE"),
            ("over", "⚽ 2.5 ÜST EN YÜKSEKLER", "OVER_YUZDE"),
            ("under", "🛡️ 2.5 ALT EN YÜKSEKLER", "UNDER_YUZDE"),
            ("kg_var", "🤝 KG VAR EN YÜKSEKLER", "KG_YUZDE"),
            ("kg_yok", "🚫 KG YOK EN YÜKSEKLER", "KGYOK_YUZDE"),
            ("iy_1", "⏱️ İY 1 EN YÜKSEKLER", "IY1_YUZDE")
        ]

        for cat_key, cat_title, perc_key in categories:
            matches = data.get(cat_key, [])
            if not matches:
                continue

            msg = f"🔥 <b>BUGÜNÜN ENLERİ ANALİZ RAPORU</b>\n"
            msg += f"📅 <i>{now_str}</i>\n"
            msg += f"⚙️ <i>Min. Maç: {min_mac} | Tolerans: ±{tolerans}</i>\n"
            msg += "───────────────────────────\n\n"
            msg += f"<b>{cat_title}</b>\n"
            msg += "📊 ───────────────────\n\n"

            for idx, item in enumerate(matches[:15], start=1):
                msg += format_match_line(idx, item, perc_key) + "\n"

            send_telegram_message(msg)

    except Exception as e:
        print(f"❌ Bugünün Enleri raporu oluşturulurken hata: {e}")


# ============================================================
# MAIN YÜKLEME AKIŞI
# ============================================================
try:
    print("🔌 Supabase veritabanına bağlanılıyor...")

    # 1. ESKİ TABLOLARI SIFIRLAMA (TRUNCATE) HAREKETİ - ÖNCELİKLİ TEMİZLİK
    with engine.begin() as conn:
        print("🧹 Veritabanı tabloları sıfırlanıyor...")
        conn.execute(text("TRUNCATE TABLE oranlar, bugun_oranlar RESTART IDENTITY CASCADE;"))

    # 2. Excel Verilerini Kontrol Et ve Yükle
    print("📂 'oranlar_kopya.xlsx' Okunuyor...")
    df_oranlar = pd.read_excel("oranlar_kopya.xlsx")
    print(f"   ℹ️ 'oranlar_kopya.xlsx' toplam {len(df_oranlar)} satır veri içeriyor.")
    df_oranlar.to_sql("oranlar", engine, if_exists="append", index=False, method="multi", chunksize=1000)
    print("✅ Geçmiş oranlar 'oranlar' tablosuna yazıldı.")

    print("📂 'bugun_oranlar_kopya.xlsx' Okunuyor...")
    df_bugun = pd.read_excel("bugun_oranlar_kopya.xlsx")
    print(f"   ℹ️ 'bugun_oranlar_kopya.xlsx' toplam {len(df_bugun)} satır veri içeriyor.")

    df_bugun.to_sql("bugun_oranlar", engine, if_exists="append", index=False, method="multi", chunksize=1000)
    print("✅ Bugünün oranları 'bugun_oranlar' tablosuna yazıldı.")

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n🎉 SUPABASE YÜKLEMESİ ANINDA BAŞARILI! ({now_str})")

    # 3. Render / Streamlit Önbelleğini Kesin Olarak Temizle
    print("\n⚡ Render Backend ve Web Önbelleği temizleniyor...")
    cache_endpoints = [
        "/api/cache-clear", "/api/clear-cache", "/clear-cache", 
        "/api/reset-cache", "/cache/clear", "/api/reload", "/?clear_cache=true"
    ]
    for endpoint in cache_endpoints:
        try:
            res = requests.get(f"{BACKEND_URL}{endpoint}", timeout=5)
            if res.status_code in [200, 201]:
                print(f"✅ Önbellek sıfırlandı -> Endpoint: {endpoint}")
        except Exception:
            pass

    print("⏳ Servisin güncellenmesi bekleniyor (5 saniye)...")
    time.sleep(5)

    # 4. Telegram Bildirimlerini Gönder
    generate_and_send_bugunun_enleri()

except Exception as e:
    print(f"\n❌ Yükleme sırasında bir hata oluştu: {e}")

print("=" * 60)
print("🏁 İŞLEM TAMAMLANDI")
print("=" * 60)