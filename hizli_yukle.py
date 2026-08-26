import os
import shutil
import subprocess
import time

ORIJINAL_BUGUN = "bugun_oranlar.xlsx"
KOPYA_BUGUN = "bugun_oranlar_kopya.xlsx"
ORIJINAL_GENEL = "oranlar.xlsx"
KOPYA_GENEL = "oranlar_kopya.xlsx"

VERCEL_REPO_URL = "https://github.com/rostova67/oran-analiz-site.git"

def bilgisayarda_kopya_olustur(orijinal, kopya):
    if os.path.exists(orijinal):
        try:
            shutil.copyfile(orijinal, kopya)
            print(f"💾 Yerel kopya güncellendi: {kopya}")
        except Exception as e:
            print(f"⚠️ Kopya hatası: {e}")

def manuel_yukle():
    print("⚡ Veriler Vercel projesine aktarılıyor...")
    
    bilgisayarda_kopya_olustur(ORIJINAL_BUGUN, KOPYA_BUGUN)
    bilgisayarda_kopya_olustur(ORIJINAL_GENEL, KOPYA_GENEL)

    try:
        # Vercel'in bağlı olduğu depoyu git adreslerine ekle
        subprocess.run(["git", "remote", "add", "vercel_repo", VERCEL_REPO_URL], stderr=subprocess.DEVNULL)
        
        subprocess.run(["git", "add", "*.xlsx", "*.py"], check=True)
        tarih = time.strftime('%Y-%m-%d %H:%M:%S')
        commit_mesaji = f"Vercel Guncelleme: ({tarih})"
        
        subprocess.run(["git", "commit", "--allow-empty", "-m", commit_mesaji], check=True)
        
        # Hem Render (backend) hem de Vercel (site) depolarına gönder
        print("⬆️ Render ve Vercel'e push ediliyor...")
        subprocess.run(["git", "push", "origin", "master", "-f"], check=True)
        subprocess.run(["git", "push", "vercel_repo", "master:main", "-f"], check=True)
        
        print(f"\n🎉 KESİN BAŞARI! Vercel tetiklendi ({tarih}).")
        print("👉 Siteniz 30 saniye içinde güncellenecektir: https://oran-analiz-site.vercel.app")

    except subprocess.CalledProcessError as e:
        print(f"\n⚠️ Hata oluştu: {e}")

if __name__ == "__main__":
    manuel_yukle()