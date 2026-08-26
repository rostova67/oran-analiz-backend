import os
import shutil
import subprocess
import sys
import time

ORIJINAL_BUGUN = "bugun_oranlar.xlsx"
KOPYA_BUGUN = "bugun_oranlar_kopya.xlsx"
ORIJINAL_GENEL = "oranlar.xlsx"
KOPYA_GENEL = "oranlar_kopya.xlsx"

def bilgisayarda_kopya_olustur(orijinal, kopya):
    if os.path.exists(orijinal):
        try:
            shutil.copyfile(orijinal, kopya)
            print(f"💾 Yerel kopya oluşturuldu: {kopya}")
        except Exception as e:
            print(f"⚠️ Kopya hatası: {e}")

def ana_surec():
    print("🚀 1. ADIM: oran.py çalıştırılıyor...")
    try:
        subprocess.run([sys.executable, "oran.py"], check=True)
        print("✅ oran.py bitti!")
    except subprocess.CalledProcessError as e:
        print(f"❌ oran.py hatası: {e}")
        return

    print("\n🔄 2. ADIM: Bilgisayar yedekleri güncelleniyor...")
    bilgisayarda_kopya_olustur(ORIJINAL_BUGUN, KOPYA_BUGUN)
    bilgisayarda_kopya_olustur(ORIJINAL_GENEL, KOPYA_GENEL)

    print("\n⬆️ 3. ADIM: Veriler Backend'e yükleniyor...")
    try:
        # Sadece Render'ın okuduğu ana Excel dosyalarını gönderir
        subprocess.run(["git", "add", ORIJINAL_BUGUN, ORIJINAL_GENEL], check=True)
        tarih = time.strftime('%Y-%m-%d %H:%M:%S')
        commit_mesaji = f"Otm Guncelleme: ({tarih})"
        subprocess.run(["git", "commit", "--allow-empty", "-m", commit_mesaji], check=True)
        
        # Sadece backend deposuna push eder (frontend deposunu bozmaz)
        subprocess.run(["git", "push", "origin", "master", "-f"], check=True)
        print(f"\n🎉 BAŞARILI! Veriler Render'a aktarıldı ({tarih}).")

    except subprocess.CalledProcessError as e:
        print(f"\n⚠️ Aktarım hatası: {e}")

if __name__ == "__main__":
    ana_surec()