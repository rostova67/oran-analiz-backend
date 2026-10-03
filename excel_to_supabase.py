import pandas as pd
from sqlalchemy import create_engine

# ⚠️ BURAYA KOPYALADIĞIN CONNECTION STRING'I YAZ
# [YOUR-PASSWORD] yazan yere Supabase veritabanı şifreni koymayı unutma!
# 'SENIN_VERITABANI_SIFREN' yazan yere Supabase projesini açarken belirlediğin şifreyi yaz
DB_URL = "postgresql://postgres:KatarinaRostova67@db.xqhdhwdgitksemfidsdi.supabase.co:5432/postgres"

print("🔌 Supabase veritabanına bağlanılıyor...")
engine = create_engine(DB_URL)

try:
    # 1. 'oranlar_kopya.xlsx' dosyasını yükle
    print("📂 'oranlar_kopya.xlsx' okunuyor...")
    df_oranlar = pd.read_excel('oranlar_kopya.xlsx')
    
    # Veriyi Supabase'e 'oranlar' tablosu olarak yaz
    print("🚀 'oranlar' tablosu Supabase'e aktarılıyor...")
    df_oranlar.to_sql('oranlar', engine, if_exists='replace', index=False)
    print("✅ Geçmiş oranlar başarıyla yüklendi!")

    # 2. 'bugun_oranlar_kopya.xlsx' dosyasını yükle
    print("📂 'bugun_oranlar_kopya.xlsx' okunuyor...")
    df_bugun = pd.read_excel('bugun_oranlar_kopya.xlsx')
    
    # Veriyi Supabase'e 'bugun_oranlar' tablosu olarak yaz
    print("🚀 'bugun_oranlar' tablosu Supabase'e aktarılıyor...")
    df_bugun.to_sql('bugun_oranlar', engine, if_exists='replace', index=False)
    print("✅ Bugünün oranları başarıyla yüklendi!")

    print("\n🎉 TÜM VERİLER SUPABASE VERİTABANINA AKTARILDI!")

except Exception as e:
    print(f"\n❌ Bir hata oluştu: {e}")