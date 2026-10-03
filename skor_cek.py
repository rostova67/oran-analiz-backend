# =========================================================
# SOFASCORE ÜZERİNDEN DÜNÜN VE SADECE 9/29 SKORLARINI ÇEKME VE TEMİZLEME
# GELİŞTİRİLMİŞ INPUT BULMA VE ATLAMAMA MEKANİZMASI
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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

GUNCEL_DOSYA = "bugun_oranlar.xlsx"
THREAD_COUNT = 4  # Paralel Chrome sayısı
BASE_PORT = 9222  # Portlar: 9222, 9223, 9224, 9225


def get_search_input(driver, timeout=10):
    """
    Arama kutusunu bulmak için çoklu strateji uygular.
    Bulamazsa Ctrl+K yapar veya JS ile tetikler.
    """
    # 1. Doğrudan input elementini dene
    try:
        input_box = driver.find_element(By.ID, "search-input")
        if input_box.is_displayed():
            return input_box
    except Exception:
        pass

    # 2. Ctrl + K kısayolunu tetikle
    try:
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.CONTROL, "k")
        time.sleep(0.5)
        input_box = driver.find_element(By.ID, "search-input")
        if input_box.is_displayed():
            return input_box
    except Exception:
        pass

    # 3. Span / Buton tıklama stratejisi
    try:
        driver.execute_script("""
            let span = document.querySelector("span.ta_start");
            if (span) { span.click(); return; }
            let btn = document.querySelector("div[class*='Sofascore']") || document.querySelector("button[aria-label*='Search']");
            if (btn) { btn.click(); }
        """)
        time.sleep(0.5)
    except Exception:
        pass

    # 4. Explicit Wait ile bekle ve dön
    return WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.ID, "search-input"))
    )


def clean_match_name(mac_adi):
    """
    Maç adındaki saati veya özel karakterleri temizleyerek 
    Sofascore aramasına en uygun formata getirir.
    Örn: '[15:30] Arsenal vs Chelsea' -> 'Arsenal vs Chelsea'
    """
    mac_adi = re.sub(r'\[.*?\]', '', str(mac_adi)).strip()
    return mac_adi


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

    toplam_parca = len(chunk_df)

    for i, (idx, row) in enumerate(chunk_df.iterrows(), 1):
        orijinal_mac_adi = str(row["MAC"]).strip()
        arama_mac_adi = clean_match_name(orijinal_mac_adi)

        # Zaten geçerli bir skor varsa atla
        if pd.notna(row["SKOR"]) and str(row["SKOR"]).strip() not in ["-", "", "nan"]:
            continue

        skor_bulundu = False
        max_deneme = 3

        for deneme in range(1, max_deneme + 1):
            try:
                # 1. Arama inputunu bul
                input_box = get_search_input(driver, timeout=5)

                # 2. JS ile eski metni temizle ve yeni maçı yaz
                driver.execute_script("arguments[0].value = '';", input_box)
                input_box.click()
                input_box.send_keys(Keys.CONTROL + "a")
                input_box.send_keys(Keys.BACKSPACE)
                time.sleep(0.2)
                input_box.send_keys(arama_mac_adi)

                print(f"🔍 [Port {port}] [{i}/{toplam_parca}] Aranıyor: {arama_mac_adi} (Bekleniyor...)")

                # 3. Aramanın yüklenmesi için esnek bekleme
                time.sleep(3.5)

                page_text = driver.find_element(By.TAG_NAME, "body").text
                lines = [l.strip() for l in page_text.split("\n") if l.strip()]

                for line_idx, line in enumerate(lines):
                    # Sadece "Dün", "Yesterday" veya tam olarak "9/29" yazan durumları kabul et
                    if line in ["Dün", "Yesterday", "9/29"]:
                        arama_alani = " ".join(lines[max(0, line_idx - 3): min(len(lines), line_idx + 4)])
                        
                        # (1:0) veya (2:1) benzeri skor kalıbını ara
                        skor_match = re.search(r'\((\d+)\s*[:|-]\s*(\d+)\)', arama_alani)

                        if skor_match:
                            bulunan_skor = f"{skor_match.group(1)}-{skor_match.group(2)}"
                            chunk_df.at[idx, "SKOR"] = bulunan_skor
                            skor_bulundu = True
                            print(f"  ✅ [Port {port}] [{i}/{toplam_parca}] SKOR BULUNDU ({line}) -> {orijinal_mac_adi}: {bulunan_skor}")
                            break

                if not skor_bulundu:
                    print(f"  ℹ️ [Port {port}] [{i}/{toplam_parca}] Dün / 9/29 Skoru Bulunamadı -> {orijinal_mac_adi}")

                break  # İşlem tamamlandıysa deneme döngüsünden çık

            except Exception as e:
                print(f"  ⚠️ [Port {port}] Input/Sayfa Hatası ({deneme}/{max_deneme}) -> {orijinal_mac_adi}: {e}")
                time.sleep(2)
                if deneme == max_deneme:
                    print(f"  ❌ [Port {port}] {orijinal_mac_adi} {max_deneme} denemeye rağmen işlenemedi!")

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
    print(f"🚀 Toplam {toplam_islem} maç taranacak...\n")

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

    print("\n" + "=" * 60)
    print("🎯 İŞLEM TAMAMLANDI!")
    print(f"💾 Excel dosyası korunarak güncellendi: '{GUNCEL_DOSYA}'")
    print("=" * 60)


if __name__ == "__main__":
    main()