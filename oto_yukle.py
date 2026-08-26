import os
import shutil
import subprocess
import sys
import time

# Dosya isimleri
ORIJINAL_BUGUN = "bugun_oranlar.xlsx"
KOPYA_BUGUN = "bugun_oranlar_kopya.xlsx"

ORIJINAL_GENEL = "oranlar.xlsx"
KOPYA_GENEL = "oranlar_kopya.xlsx"

def bilgisayarda_kopya_olustur(orijinal, kopya):
    """Sadece bilgisayarda yedek kalması için kopyasını oluşturur."""
    if os.path.exists(orijinal):
        try:
            shutil.copyfile(orijinal, kopya)
            print(f"💾 Yerel kopya oluşturuldu: {kopya}")
        except Exception as e:
            print(f"⚠️ Kopya hatası: {e}")

def ana_surec():
    print("🚀 1. ADIM: oran.py çalıştırılıyor, maçlar çekiliyor...")
    
    try:
        subprocess.run([sys.executable, "oran.py"], check=True)
        print("✅ oran.py çalışmasını tamamladı!")
    except subprocess.CalledProcessError as e:
        print(f"❌ oran.py çalışırken bir hata oluştu: {e}")
        return

    print("\n🔄 2. ADIM: Yerel yedek kopyalar güncelleniyor...")
    bilgisayarda_kopya_olustur(ORIJINAL_BUGUN, KOPYA_BUGUN)
    bilgisayarda_kopya_olustur(ORIJINAL_GENEL, KOPYA_GENEL)

    print("\n⬆️ 3. ADIM: GitHub ve Vercel Güncelleniyor...")
    try:
        # Excel dosyalarını takibe al
        subprocess.run(["git", "add", ORIJINAL_BUGUN, ORIJINAL_GENEL], check=True)
        
        tarih = time.strftime('%Y-%m-%d %H:%M:%S')
        commit_mesaji = f"Otm: Oranlar güncellendi ({tarih})"
        subprocess.run(["git", "commit", "-m", commit_mesaji], check=True)
        
        # 1. Backend Repository'sine Gönder
        subprocess.run(["git", "push", "origin", "master"], check=True)
        
        # 2. Vercel'in Bağlı Olduğu Main/Master Dalına Zorla Gönder
        subprocess.run(["git", "push", "origin", "HEAD:main"], check=True)
        
        print(f"\n🎉 BAŞARILI! Veriler Vercel ve Render'a gönderildi ({tarih}).")
        print("👉 Siteniz 1 dakika içinde güncellenecektir: https://oran-analiz-site.vercel.app")

    except subprocess.CalledProcessError as e:
        print(f"\n⚠️ Aktarım sırasında bir sorun oluştu: {e}")

if __name__ == "__main__":
    ana_surec()