import pandas as pd
from sqlalchemy import create_engine
import requests
import datetime

print("=" * 60)
print("⚡ HIZLI SUPABASE YÜKLEMESİ BAŞLIYOR")
print("=" * 60)

# ============================================================
# VERİTABANI BAĞLANTISI (SUPABASE)
# ============================================================
DB_URL = "postgresql://postgres:KatarinaRostova67@db.xqhdhwdgitksemfidsdi.supabase.co:5432/postgres"
engine = create_engine(DB_URL)

try:
    print("\n🔌 Supabase veritabanına bağlanılıyor...")
    
    # 1. Geçmiş Oranlar Yükleniyor
    print("📂 'oranlar_kopya.xlsx' Supabase'e aktarılıyor...")
    df_oranlar = pd.read_excel("oranlar_kopya.xlsx")
    df_oranlar.to_sql("oranlar", engine, if_exists="replace", index=False)
    print("✅ Geçmiş oranlar 'oranlar' tablosuna yazıldı.")

    # 2. Bugünün Oranları Yükleniyor
    print("📂 'bugun_oranlar_kopya.xlsx' Supabase'e aktarılıyor...")
    df_bugun = pd.read_excel("bugun_oranlar_kopya.xlsx")
    df_bugun.to_sql("bugun_oranlar", engine, if_exists="replace", index=False)
    print("✅ Bugünün oranları 'bugun_oranlar' tablosuna yazıldı.")

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n🎉 SUPABASE YÜKLEMESİ ANINDA BAŞARILI! ({now_str})")

    # 3. Backend Önbelleğini Temizle
    print("\n⚡ Render Backend önbelleği güncelleniyor...")
    try:
        res = requests.get("https://oran-analiz-backend.onrender.com/api/cache-clear", timeout=10)
        if res.status_code == 200:
            print("✅ Backend önbelleği başarıyla sıfırlandı! Yeni veriler yayında.")
        else:
            print("⚠️ Önbellek tetikleme uyarısı:", res.status_code)
    except Exception as e:
        print("⚠️ Backend önbellek sıfırlama isteği gönderilemedi (Sunucu uyuyor olabilir).")

except Exception as e:
    print(f"\n❌ Yükleme sırasında bir hata oluştu: {e}")

print("=" * 60)
print("🏁 HIZLI YÜKLEME TAMAMLANDI")
print("=" * 60)