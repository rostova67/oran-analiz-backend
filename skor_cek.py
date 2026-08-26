# =========================================================
# SOFASCORE ÜZERİNDEN DÜNÜN SKORLARINI ÇEKME VE TEMİZLEME
# 3 PARALEL CHROME (20 SANİYE GÜVENLİ BEKLEME SÜRELİ)
# =========================================================

import os
import re
import time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

GUNCEL_DOSYA = "bugun_oranlar.xlsx"
THREAD_COUNT = 4  # 3 Paralel Chrome
BASE_PORT = 9222  # Portlar: 9222, 9223, 9224


def process_chunk(chunk_df, port):
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(15)
        print(f"🔗 [Port {port}] Chrome'a bağlandı, arama başlatılıyor...")
    except Exception as e:
        print(f"❌ [Port {port}] Chrome bağlantı hatası: {e}")
        return chunk_df

    bulunan_skor_sayisi = 0
    toplam_parca = len(chunk_df)

    for i, (idx, row) in enumerate(chunk_df.iterrows(), 1):
        orijinal_mac_adi = str(row["MAC"]).strip()

        # Zaten geçerli bir skor varsa atla
        if pd.notna(row["SKOR"]) and str(row["SKOR"]).strip() not in ["-", "", "nan"]:
            continue

        try:
            # 1. Arama inputunu bul
            try:
                input_box = driver.find_element(By.ID, "search-input")
            except:
                driver.execute_script("""
                    let btn = document.querySelector("div[class*='Sofascore']") || document.querySelector("button[aria-label*='Search']");
                    if(btn) btn.click();
                """)
                time.sleep(1)
                input_box = driver.find_element(By.ID, "search-input")

            # 2. Eski metni temizle ve yeni maçı yaz
            input_box.click()
            input_box.send_keys(Keys.CONTROL + "a")
            input_box.send_keys(Keys.BACKSPACE)
            time.sleep(0.5)
            input_box.send_keys(orijinal_mac_adi)

            print(f"🔍 [Port {port}] [{i}/{toplam_parca}] Aranıyor: {orijinal_mac_adi} (20 sn bekleniyor...)")
            
            # 3. Aramanın gelmesi ve sistemin rahatlaması için 20 SANİYE BEKLE
            time.sleep(10)

            skor_bulundu = False
            page_text = driver.find_element(By.TAG_NAME, "body").text
            lines = [l.strip() for l in page_text.split("\n") if l.strip()]

            for line_idx, line in enumerate(lines):
                # Sadece "Dün" veya "Yesterday" etiketlerini kontrol et
                if line in ["Dün", "Yesterday"]:
                    arama_alani = " ".join(lines[max(0, line_idx-3): min(len(lines), line_idx+4)])
                    skor_match = re.search(r'\((\d+:\d+)\)', arama_alani)
                    
                    if skor_match:
                        bulunan_skor = skor_match.group(1).replace(":", "-")
                        chunk_df.at[idx, "SKOR"] = bulunan_skor
                        bulunan_skor_sayisi += 1
                        skor_bulundu = True
                        print(f"  ✅ [Port {port}] [{i}/{toplam_parca}] SKOR BULUNDU -> {orijinal_mac_adi}: {bulunan_skor}")
                        break

            if not skor_bulundu:
                print(f"  ℹ️ [Port {port}] [{i}/{toplam_parca}] Dün Skoru Bulunamadı -> {orijinal_mac_adi}")

        except Exception as e:
            print(f"  ⚠️ [Port {port}] Hata/Atlandı ({orijinal_mac_adi}): {e}")

    return chunk_df


def main():
    if not os.path.exists(GUNCEL_DOSYA):
        print(f"❌ '{GUNCEL_DOSYA}' bulunamadı!")
        return

    df_bugun = pd.read_excel(GUNCEL_DOSYA)
    if df_bugun.empty:
        print(f"❌ '{GUNCEL_DOSYA}' boş!")
        return

    if "SKOR" not in df_bugun.columns:
        df_bugun["SKOR"] = "-"

    islem_gorecekler = df_bugun[
        df_bugun["SKOR"].isna() | df_bugun["SKOR"].astype(str).str.strip().isin(["-", "", "nan"])
    ]
    
    if islem_gorecekler.empty:
        print("✅ Tüm maçların skorları zaten mevcut!")
        return

    toplam_islem = len(islem_gorecekler)
    print(f"🚀 Toplam {toplam_islem} maç taranacak (Her maç için 20 saniye bekleniyor)...\n")

    chunks = [islem_gorecekler.iloc[i::THREAD_COUNT].copy() for i in range(THREAD_COUNT)]
    updated_chunks = []

    with ThreadPoolExecutor(max_workers=THREAD_COUNT) as executor:
        futures = []
        for i in range(THREAD_COUNT):
            port = BASE_PORT + i
            futures.append(executor.submit(process_chunk, chunks[i], port))

        for future in as_completed(futures):
            res_df = future.result()
            updated_chunks.append(res_df)

    df_final = df_bugun.copy()
    for u_chunk in updated_chunks:
        df_final.update(u_chunk)

    df_final.to_excel(GUNCEL_DOSYA, index=False)

    print("\n" + "="*60)
    print("🎯 İŞLEM TAMAMLANDI!")
    print(f"💾 Excel dosyası korunarak güncellendi: '{GUNCEL_DOSYA}'")
    print("="*60)

if __name__ == "__main__":
    main()