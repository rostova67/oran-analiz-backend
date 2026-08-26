# =========================================================
# ORAN PANELİ - BİTEN MAÇLARI ARŞİVLEME VE LİSTE TEMİZLEME
# =========================================================

import os
import pandas as pd

BUGUN_DOSYA = "bugun_oranlar.xlsx"
ORANLAR_DOSYA = "oranlar.xlsx"

def main():
    if not os.path.exists(BUGUN_DOSYA):
        print(f"❌ '{BUGUN_DOSYA}' dosyası bulunamadı!")
        return

    df_bugun = pd.read_excel(BUGUN_DOSYA)

    if df_bugun.empty:
        print(f"ℹ️ '{BUGUN_DOSYA}' dosyası zaten boş.")
        return

    if "SKOR" not in df_bugun.columns:
        print(f"❌ '{BUGUN_DOSYA}' içinde 'SKOR' sütunu bulunamadı!")
        return

    # 1. Skoru geçerli olan (dolmuş) maçları ayır
    # (Boş, NaN, '-' olmayan geçerli skorlu maçlar)
    gecerli_skor_mask = (
        df_bugun["SKOR"].notna() & 
        ~df_bugun["SKOR"].astype(str).str.strip().isin(["-", "", "nan", "None"])
    )

    df_skorlu = df_bugun[gecerli_skor_mask].copy()
    df_skorsuz = df_bugun[~gecerli_skor_mask].copy()

    toplam_mac = len(df_bugun)
    skorlu_sayi = len(df_skorlu)
    skorsuz_sayi = len(df_skorsuz)

    print(f"📊 Toplam Maç: {toplam_mac}")
    print(f"✅ Skoru Alınan (Aktarılacak): {skorlu_sayi}")
    print(f"🗑️ Skoru Olmayan (Silinecek): {skorsuz_sayi}\n")

    # 2. Skoru olanları oranlar.xlsx dosyasına aktar/ekle
    if skorlu_sayi > 0:
        if os.path.exists(ORANLAR_DOSYA):
            try:
                df_oranlar = pd.read_excel(ORANLAR_DOSYA)
                df_oranlar_yeni = pd.concat([df_oranlar, df_skorlu], ignore_index=False)
            except Exception as e:
                print(f"⚠️ '{ORANLAR_DOSYA}' okunurken hata oluştu, yeni dosya oluşturuluyor: {e}")
                df_oranlar_yeni = df_skorlu
        else:
            df_oranlar_yeni = df_skorlu

        df_oranlar_yeni.to_excel(ORANLAR_DOSYA, index=False)
        print(f"💾 {skorlu_sayi} adet skorlu maç '{ORANLAR_DOSYA}' dosyasına başarıyla eklendi.")
    else:
        print("ℹ️ Aktarılacak skorlu maç bulunamadı.")

    # 3. bugun_oranlar.xlsx dosyasını tamamen temizle (Yeni maç çekimi için)
    # Sadece sütun başlıkları kalacak şekilde boş dataframe oluşturulur
    df_bos = pd.DataFrame(columns=df_bugun.columns)
    df_bos.to_excel(BUGUN_DOSYA, index=False)

    print("\n" + "="*60)
    print("🎯 AKTARIM VE TEMİZLİK TAMAMLANDI!")
    print(f"❌ Skorsuz {skorsuz_sayi} maç silindi.")
    print(f"✨ '{BUGUN_DOSYA}' sıfırlandı, yeni maç çekimi için hazır.")
    print("="*60)

if __name__ == "__main__":
    main()