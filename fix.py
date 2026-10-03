# =========================================================
# ORAN PANELİ - BİTEN MAÇLARI ARŞİVLEME VE LİSTE TEMİZLEME
# =========================================================

import os
import pandas as pd

BUGUN_DOSYA = "bugun_oranlar.xlsx"
ORANLAR_DOSYA = "oranlar.xlsx"


def save_to_excel_safe(df, file_path, index=False):
    """
    Excel dosyası açıksa çökmeyi önlemek için güvenli kaydetme fonksiyonu.
    """
    try:
        df.to_excel(file_path, index=index)
        return True
    except PermissionError:
        print(f"\n❌ HATA: '{file_path}' dosyası şu an başka bir programda (örn. Excel) açık!")
        print("   Lütfen dosyayı kapatıp tekrar deneyin.\n")
        return False
    except Exception as e:
        print(f"\n❌ Kaydetme sırasında bilinmeyen bir hata oluştu: {e}\n")
        return False


def main():
    if not os.path.exists(BUGUN_DOSYA):
        print(f"❌ '{BUGUN_DOSYA}' dosyası bulunamadı!")
        return

    try:
        df_bugun = pd.read_excel(BUGUN_DOSYA)
    except Exception as e:
        print(f"❌ '{BUGUN_DOSYA}' okunurken hata oluştu: {e}")
        return

    if df_bugun.empty:
        print(f"ℹ️ '{BUGUN_DOSYA}' dosyası zaten boş.")
        return

    if "SKOR" not in df_bugun.columns:
        print(f"❌ '{BUGUN_DOSYA}' içinde 'SKOR' sütunu bulunamadı!")
        return

    # 1. Skoru geçerli olan (dolmuş) maçları ayır
    # (Boş, NaN, '-', 'None', 'nan' olmayan geçerli skorlu maçlar)
    gecerli_skor_mask = (
        df_bugun["SKOR"].notna() & 
        ~df_bugun["SKOR"].astype(str).str.strip().isin(["-", "", "nan", "None", "null"])
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
                # ignore_index=True yaparak indekslerin çakışmasını/mükerrer olmasını engelliyoruz
                df_oranlar_yeni = pd.concat([df_oranlar, df_skorlu], ignore_index=True)
            except Exception as e:
                print(f"⚠️ '{ORANLAR_DOSYA}' okunurken hata oluştu, sıfırdan oluşturulacak: {e}")
                df_oranlar_yeni = df_skorlu
        else:
            df_oranlar_yeni = df_skorlu

        # Tamamen aynı olan mükerrer kayıtları engelle (Opsiyonel Güvence)
        df_oranlar_yeni = df_oranlar_yeni.drop_duplicates()

        # Kaydetme işlemi
        if not save_to_excel_safe(df_oranlar_yeni, ORANLAR_DOSYA, index=False):
            print("⚠️ Arşivleme işlemi tamamlanamadığı için liste temizlenmedi!")
            return
            
        print(f"💾 {skorlu_sayi} adet skorlu maç '{ORANLAR_DOSYA}' dosyasına başarıyla eklendi.")
    else:
        print("ℹ️ Aktarılacak skorlu maç bulunamadı.")

    # 3. bugun_oranlar.xlsx dosyasını tamamen temizle (Yeni maç çekimi için)
    # Sadece sütun başlıkları kalacak şekilde boş dataframe oluşturulur
    df_bos = pd.DataFrame(columns=df_bugun.columns)
    
    if save_to_excel_safe(df_bos, BUGUN_DOSYA, index=False):
        print("\n" + "="*60)
        print("🎯 AKTARIM VE TEMİZLİK TAMAMLANDI!")
        print(f"❌ Skorsuz {skorsuz_sayi} maç silindi.")
        print(f"✨ '{BUGUN_DOSYA}' sıfırlandı, yeni maç çekimi için hazır.")
        print("="*60)


if __name__ == "__main__":
    main()