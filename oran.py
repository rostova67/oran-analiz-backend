# =========================================================
# BUGÜNÜN MAÇLARINI VE ORANLARINI ÇEKME SİSTEMİ (oran.py)
# =========================================================

import os
import re
import time
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

BUGUN_FILE = "bugun_oranlar.xlsx"

# Chrome Debug Portu (Ana tarama için 9222 kullanılır)
DEBUG_PORT = 9222 

def invalid_team(text):
    text = str(text).strip()
    text_lower = text.lower()
    
    invalid_words = [
        "bugün", "bugun", "yarın", "yarin", "canlı", "futbol", "basketbol", "tenis", 
        "voleybol", "motor sporları", "mma", "e-spor", "dart", 
        "buz hokeyi", "favoriler", "tümü", "takım", "oyuncu", 
        "hakem", "stadyum", "ev sahibi", "deplasman", "üst", "alt",
        "ev sa...", "berabere", "deplas...", "içinde", "maç sonucu", "karşılıklı gol",
        "tff 1. lig", "türkiye süper lig", "süper lig", "1. lig"
    ]
    
    if text_lower in invalid_words: return True
    if re.match(r"^\d+\.\d+$", text): return True
    if re.search(r"\d{2}:\d{2}", text): return True
    if re.match(r"^\d{2}/\d{2}$", text): return True
    if "dakika içinde" in text_lower or "dakika" in text_lower: return True
    if text.isdigit() and len(text) <= 3 and not ("76" in text or "1907" in text): return True 
    return False


def find_time(block_lines):
    for line in block_lines:
        line_str = str(line).strip()
        line_lower = line_str.lower()

        if "yarın" in line_lower or "yarin" in line_lower or re.search(r"\d{2}/\d{2}", line_str):
            return None

        if "dakika" in line_lower and "içinde" in line_lower:
            dakika_match = re.search(r"(\d+)\s*dakika", line_lower)
            if dakika_match:
                return f"{dakika_match.group(1)} dakika içinde"
            return "Dakika içinde"

        if "bugün" in line_lower or "bugun" in line_lower:
            saat_match = re.search(r"\d{2}:\d{2}", line_str)
            if saat_match:
                return f"Bugün {saat_match.group(0)}"
            return "Bugün"

    return None


def main():
    chrome_options = Options()
    chrome_options.debugger_address = f"127.0.0.1:{DEBUG_PORT}"

    try:
        driver = webdriver.Chrome(options=chrome_options)
        print(f"✅ Chrome debug bağlantısı başarılı! (Port: {DEBUG_PORT})")
    except Exception as e:
        print(f"❌ Chrome debug bağlantısı kurulamadı! Hata: {e}")
        return

    driver.switch_to.window(driver.window_handles[-1])
    print(f"🔗 Aktif sekmeye bağlanıldı: {driver.title}")

    # IFRAME Kontrolü
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    if len(iframes) > 0:
        try:
            driver.switch_to.frame(iframes[0])
            print("📥 IFRAME içine geçiş yapıldı.")
            time.sleep(1)
        except:
            pass

    all_matches = []
    print("🔄 Sol menü taranıyor, ülkeler seçilip 5 saniye beklenecek...")

    country_index = 0

    while True:
        try:
            country_anchors = driver.find_elements(By.XPATH, "//a[contains(@class, 'OM-MenuItem__Anchor--locations')]")
            
            if not country_anchors or country_index >= len(country_anchors):
                print("🏁 Taranacak başka ülke kalmadı.")
                break

            target_anchor = country_anchors[country_index]
            try:
                country_name = target_anchor.text.strip().split("\n")[0]
            except:
                country_name = f"Ülke-{country_index + 1}"

            print(f"\n🌍 [{country_index + 1}/{len(country_anchors)}] Ülke Seçiliyor: {country_name}")

            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_anchor)
            time.sleep(0.3)
            driver.execute_script("arguments[0].click();", target_anchor)
            
            print("⏳ Maçların tam yüklenmesi için 5 saniye bekleniyor...")
            time.sleep(5)

            try:
                body_text = driver.find_element(By.TAG_NAME, "body").text
            except Exception:
                time.sleep(1)
                body_text = driver.find_element(By.TAG_NAME, "body").text

            lines = body_text.split("\n")

            match_start_indices = []
            for idx, line in enumerate(lines):
                cleaned = line.strip()
                if cleaned.startswith("Ev Sahibi") or cleaned.startswith("Ev Sa..."):
                    match_start_indices.append(idx)

            match_chunks = []
            for i in range(len(match_start_indices)):
                start_idx = match_start_indices[i]
                end_idx = match_start_indices[i+1] if i + 1 < len(match_start_indices) else len(lines)
                extended_start = max(0, start_idx - 35)
                chunk = lines[extended_start:end_idx]
                match_chunks.append((start_idx - extended_start, chunk))

            for local_ev_sahibi_idx, chunk in match_chunks:
                try:
                    time_chunk = chunk[max(0, local_ev_sahibi_idx - 6): local_ev_sahibi_idx]
                    saat = find_time(time_chunk)
                    
                    if saat is None:
                        continue

                    teams = []
                    search_back = 1
                    while search_back <= 30:
                        target_idx = local_ev_sahibi_idx - search_back
                        if target_idx < 0: break
                        previous_line = chunk[target_idx].strip()
                        if invalid_team(previous_line):
                            search_back += 1
                            continue
                        teams.append(previous_line)
                        if len(teams) == 2: break
                        search_back += 1

                    if len(teams) < 2: continue

                    away_team, home_team = teams[0], teams[1]

                    bad_patterns = [r"\d+'", r"1\. yarı", r"2\. yarı", r"devre arası"]
                    if any(re.search(pat, home_team.lower()) or re.search(pat, away_team.lower()) for pat in bad_patterns):
                        continue

                    oran_havuzu = []
                    for k in range(local_ev_sahibi_idx + 1, min(local_ev_sahibi_idx + 15, len(chunk))):
                        pot = chunk[k].strip()
                        if re.match(r"^\d+\.\d+$", pot):
                            oran_havuzu.append(float(pot))
                        if len(oran_havuzu) == 3: break
                    
                    if len(oran_havuzu) == 3:
                        ms1, msx, ms2 = oran_havuzu
                    else:
                        continue

                    ust, alt = None, None
                    for j in range(len(chunk)):
                        line_val = chunk[j].strip()
                        if line_val in ["ÜST", "UST", "ALT"]:
                            for k in range(j+1, min(j+4, len(chunk))):
                                potential = chunk[k].strip()
                                if re.match(r"^\d+\.\d+$", potential) and float(potential) != 2.5:
                                    if line_val in ["ÜST", "UST"]: ust = float(potential)
                                    else: alt = float(potential)
                                    break

                    mac = f"{home_team} vs {away_team}"
                    print(f"  ⚽ Eklenen Maç: {mac} | ⏰ {saat}")

                    all_matches.append({
                        "MAC": mac,
                        "MS1": ms1,
                        "MSX": msx,
                        "MS2": ms2,
                        "UST_2_5": ust,
                        "ALT_2_5": alt,
                        "SKOR": "-"
                    })

                except Exception:
                    pass

            country_index += 1

        except Exception as e:
            print(f"⚠️ Geçiş/Okuma hatası atlandı: {e}")
            country_index += 1
            if country_index > 150:
                break

    if len(all_matches) > 0:
        df = pd.DataFrame(all_matches)
        df = df.drop_duplicates(subset=["MAC"], keep="first")
        df.to_excel(BUGUN_FILE, index=False)
        
        print("\n" + "=" * 60)
        print("🎯 BUGÜNÜN TÜM MAÇLARI EKSİKSİZ KAYDEDİLDİ")
        print(f"📂 Kayıt Yolu: {BUGUN_FILE}")
        print(f"📈 Çekilen Toplam Maç Sayısı: {len(df)}")
        print("=" * 60 + "\n")
    else:
        print("\n❌ Hata: Uygun Bugün maçları bulunamadı veya kaydedilemedi!\n")

if __name__ == "__main__":
    main()