import os
import shutil
import subprocess
import time

ORIJINAL_BUGUN = "bugun_oranlar.xlsx"
KOPYA_BUGUN = "bugun_oranlar_kopya.xlsx"

ORIJINAL_GENEL = "oranlar.xlsx"
KOPYA_GENEL = "oranlar_kopya.xlsx"

def bilgisayarda_kopya_olustur(orijinal, kopya):
    if os.path.exists(orijinal):
        try:
            shutil.copyfile(orijinal, kopya)
            print(f"💾 Yerel kopya güncellendi: {kopya}")
        except Exception as e:
            print(f"⚠️ Kopya hatası: {e}")

def manuel_yukle():
    print("⚡ Hazır veriler GitHub ve Vercel'e aktarılıyor...")
    
    # 1. Bilgisayardaki kopyaları yenile
    bilgisayarda_kopya_olustur(ORIJINAL_BUGUN, KOPYA_BUGUN)
    bilgisayarda_kopya_olustur(ORIJINAL_GENEL, KOPYA_GENEL)

    # 2. Git işlemlerini çalıştır
    try:
        print("📦 Sadece Excel ve kod dosyaları takibe alınıyor...")
        # venv klasörünü es geçip sadece xlsx ve py dosyalarını ekliyoruz
        subprocess.run(["git", "add", "*.xlsx", "*.py"], check=True)
        
        tarih = time.strftime('%Y-%m-%d %H:%M:%S')
        commit_mesaji = f"Manuel Yukleme: Oranlar guncellendi ({tarih})"
        
        subprocess.run(["git", "commit", "--allow-empty", "-m", commit_mesaji], check=True)
        
        # Hem master hem main dallarına push et
        print("⬆️ GitHub'a gönderiliyor...")
        subprocess.run(["git", "push", "origin", "master"], check=True)
        subprocess.run(["git", "push", "origin", "master:main"], check=True)
        
        print(f"\n🎉 İŞLEM TAMAM! Veriler başarıyla gönderildi ({tarih}).")
        print("👉 Siteniz 30-60 saniye içinde güncellenecektir: https://oran-analiz-site.vercel.app")

    except subprocess.CalledProcessError as e:
        print(f"\n⚠️ Aktarım sırasında bir durum oluştu: {e}")

if __name__ == "__main__":
    manuel_yukle()