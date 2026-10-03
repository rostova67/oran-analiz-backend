import os
import re
import time
import requests
import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# ================= AYARLAR =================
TELEGRAM_TOKEN = "8998074343:AAFGmLOpcS7v3SUPVqPr6aV3kyqjG2lLcy0"
TELEGRAM_CHAT_ID = "8464565138"
EXCEL_BUGUN = "bugun_oranlar.xlsx"
EXCEL_GECMIS = "oranlar.xlsx"
DEBUG_PORT = 9222
CHECK_INTERVAL = 30  # Tarama sıklığı (saniye)

MIN_SAMPLE_COUNT = 5        # En az 5 geçmiş maç eşleşmeli
MIN_PROBABILITY_PCT = 75.0  # En az %75 kazanma/gol olasılığı
BILDIRIM_GONDERILENLER = set()

# ================= YARDIMCI VE ANALİZ FONKSİYONLARI =================

def telegram_mesaj_gonder(mesaj: str):
    if TELEGRAM_TOKEN == "BOT_TOKENINIZI_BURAYA_YAZIN":
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mesaj, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"⚠️ Telegram gönderme hatası: {e}")

def load_excel_data(file_path: str) -> pd.DataFrame:
    """Excel dosyalarını yükler ve sayısal oranları temziler."""
    if not os.path.exists(file_path):
        return pd.DataFrame()
    try:
        df = pd.read_excel(file_path)
        for col in ["MS1", "MSX", "MS2", "UST_2_5", "ALT_2_5"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    except Exception as e:
        print(f"⚠️ Excel yükleme hatası ({file_path}): {e}")
        return pd.DataFrame()

def is_valid_team(text: str) -> bool:
    """Bahis başlıklarını ve sabit arayüz kelimelerini filtreler."""
    t = text.strip().upper()
    if not t: return False
    
    YASAKLILAR = [
        "EV SAHIBI", "BERABERE", "DEPLASMAN", "ÜST", "ALT", "EVET", "HAYIR", 
        "MAÇ SONUCU", "ÜST/ALT", "KARŞILIKLI GOL", "1", "X", "2", 
        "1. YARI", "2. YARI", "DEVRE ARASI"
    ]
    if t in YASAKLILAR: return False
    if re.match(r"^\d+\.\d+$", t): return False 
    if re.search(r"\d+'", t): return False      
    if t.isdigit(): return False                
    if len(t) < 2: return False
    
    if any(header in t for header in ["LIGA", "GROUP", "TERRITORY", "LEAGUE", "CUP", "DIVISION", "KLÜPLER", "HAZIRLIK", "REGIONAL"]): 
        return False
        
    return True

def parse_score(score_str: Any) -> Optional[tuple]:
    try:
        if pd.isna(score_str): return None
        parts = str(score_str).strip().split("-")
        if len(parts) == 2:
            return int(parts[0]), int(parts[1])
    except Exception:
        pass
    return None

def find_similar_matches(history_df: pd.DataFrame, ms1: float, msx: float, ms2: float, ust: float, alt: float) -> pd.DataFrame:
    """Maç önü oranlarıyla çeyrekli duyarlılıkla (1.5, 1.75, 2.5, 2.75) geçmiş maçları arar."""
    if history_df.empty:
        return pd.DataFrame()

    tolerances = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
    for tol in tolerances:
        cond = (
            (history_df["MS1"].between(ms1 - tol, ms1 + tol)) &
            (history_df["MSX"].between(msx - tol, msx + tol)) &
            (history_df["MS2"].between(ms2 - tol, ms2 + tol)) &
            (history_df["UST_2_5"].between(ust - tol, ust + tol)) &
            (history_df["ALT_2_5"].between(alt - tol, alt + tol))
        )
        filtered = history_df[cond].copy()
        if len(filtered) >= MIN_SAMPLE_COUNT:
            return filtered
            
    return pd.DataFrame()

# ================= CANLI EKRAN TARAMA VE ANALİZ =================

def canli_ekrani_tara_ve_analiz_et():
    chrome_options = Options()
    chrome_options.debugger_address = f"127.0.0.1:{DEBUG_PORT}"

    try:
        driver = webdriver.Chrome(options=chrome_options)
    except Exception as e:
        print(f"❌ Chrome debug bağlantısı kurulamadı! Hata: {e}")
        return

    driver.switch_to.default_content()
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    if len(iframes) > 0:
        try:
            driver.switch_to.frame(iframes[0])
        except:
            pass

    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
    except Exception:
        driver.switch_to.default_content()
        return

    lines = [line.strip() for line in body_text.split("\n") if line.strip()]
    yakalanan_maclar = []

    for i, line in enumerate(lines):
        if line in ["1. Yarı", "2. Yarı", "Devre Arası"]:
            durum_str = line
            
            # 1. Dakikayı Çek
            dakika_str = "0'"
            dakika_int = 0
            for k in range(max(0, i - 2), min(len(lines), i + 2)):
                if "'" in lines[k]:
                    dakika_str = lines[k]
                    m = re.search(r"(\d+)", dakika_str)
                    if m: dakika_int = int(m.group(1))
                    break

            # 2. Takımları Çek
            aday_takimlar = []
            for k in range(i + 1, min(len(lines), i + 12)):
                if is_valid_team(lines[k]):
                    aday_takimlar.append(lines[k])
                if len(aday_takimlar) == 2:
                    break

            if len(aday_takimlar) < 2:
                aday_takimlar = []
                for k in range(max(0, i - 5), i):
                    if is_valid_team(lines[k]):
                        aday_takimlar.append(lines[k])

            if len(aday_takimlar) < 2:
                continue

            ev_takim = aday_takimlar[0]
            dep_takim = aday_takimlar[1]

            # 3. KESİN SKOR TESPİTİ
            ev_skor, dep_skor = "0", "0"
            try:
                ev_elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{ev_takim}')]/ancestor::*[position()<=3]")
                for elem in ev_elements:
                    score_nodes = elem.find_elements(By.XPATH, ".//*[text() and string-length(text()) <= 2]")
                    found_scores = []
                    for node in score_nodes:
                        txt = node.text.strip()
                        if txt.isdigit() and int(txt) <= 20:
                            found_scores.append(txt)
                    
                    if len(found_scores) >= 2:
                        ev_skor = found_scores[0]
                        dep_skor = found_scores[1]
                        break
            except Exception:
                pass

            if int(ev_skor) > 20: ev_skor = "0"
            if int(dep_skor) > 20: dep_skor = "0"

            # 4. ORANLAR VE BARAJ TESPİTİ
            sonraki_mac_sınırı = min(len(lines), i + 35)
            for j in range(i + 1, len(lines)):
                if lines[j] in ["1. Yarı", "2. Yarı", "Devre Arası"]:
                    sonraki_mac_sınırı = j
                    break

            mac_blogu = lines[i:sonraki_mac_sınırı]
            oranlar = []
            baraj_degeri = "2.5"
            POSSIBLE_BARAJS = ["0.5", "0.75", "1.25", "1.5", "1.75", "2.25", "2.5", "2.75", "3.25", "3.5", "4.5"]

            for val in mac_blogu:
                if val in POSSIBLE_BARAJS and baraj_degeri == "2.5":
                    baraj_degeri = val
                    continue

                if re.match(r"^\d+\.\d+$", val):
                    oranlar.append(val)
                elif val in ["🔒", "kilitli", "lock"] or "🔒" in val:
                    oranlar.append("🔒")

            while len(oranlar) < 7:
                oranlar.append("🔒")

            oranlar = oranlar[:7]
            mac_adi = f"{ev_takim} vs {dep_takim}"

            if any(m['MAC'] == mac_adi for m in yakalanan_maclar):
                continue

            yakalanan_maclar.append({
                "MAC": mac_adi, "EV": ev_takim, "DEP": dep_takim,
                "DAKIKA_INT": dakika_int, "DAKIKA_STR": dakika_str, "DURUM": durum_str,
                "SKOR": f"{ev_skor}-{dep_skor}", "BARAJ": baraj_degeri,
                "MS1": oranlar[0], "MSX": oranlar[1], "MS2": oranlar[2],
                "UST": oranlar[3], "ALT": oranlar[4],
                "KG_VAR": oranlar[5], "KG_YOK": oranlar[6]
            })

    driver.switch_to.default_content()

    # Terminal Arayüz Çıktısı
    print("\n" + "=" * 75)
    print(f"  [🔄 {time.strftime('%H:%M:%S')}] CANLI MAÇ TARAMA SONUÇLARI (Toplam: {len(yakalanan_maclar)})")
    print("=" * 75 + "\n")

    today_df = load_excel_data(EXCEL_BUGUN)
    history_df = load_excel_data(EXCEL_GECMIS)

    for idx, mac in enumerate(yakalanan_maclar, 1):
        ev, dep = mac['EV'], mac['DEP']
        dk_str, skor, durum = mac['DAKIKA_STR'], mac['SKOR'], mac['DURUM']
        baraj = mac['BARAJ']
        
        print(f"[{idx:02d}] ⚽ {ev} vs {dep}")
        print(f"     📊 Skor: {skor} | ⏱️ {durum} ({dk_str})")
        print(f"     📈 Canlı MS : [1: {mac['MS1']} | X: {mac['MSX']} | 2: {mac['MS2']}]")
        print(f"     🎯 {baraj:<3}      : [Üst: {mac['UST']} | Alt: {mac['ALT']}]")
        print("-" * 60)

        # ================= ANALİZ MOTORU VE EŞLEŞTİRME =================
        if today_df.empty or history_df.empty:
            continue

        # 1. Maç bugün_oranlar.xlsx dosyasında var mı? (İsim bazlı esnek arama)
        matched_rows = today_df[
            today_df.apply(lambda r: (str(r.get('Ev Sahibi', '')).lower().strip() in ev.lower() or ev.lower() in str(r.get('Ev Sahibi', '')).lower().strip()) and
                                     (str(r.get('Deplasman', '')).lower().strip() in dep.lower() or dep.lower() in str(r.get('Deplasman', '')).lower().strip()), axis=1)
        ]

        if matched_rows.empty:
            continue

        match_row = matched_rows.iloc[0]

        try:
            # 2. Maç Önü Oranlarını Al
            ms1 = float(match_row["MS1"])
            msx = float(match_row["MSX"])
            ms2 = float(match_row["MS2"])
            ust = float(match_row["UST_2_5"])
            alt = float(match_row["ALT_2_5"])

            # 3. Tarihsel Eşleşen Maçları Çıkar
            similar_df = find_similar_matches(history_df, ms1, msx, ms2, ust, alt)
            if len(similar_df) < MIN_SAMPLE_COUNT:
                continue

            # 4. İstatistiksel Hesaplama
            parsed_canli = parse_score(skor)
            if not parsed_canli: continue
            ev_canli, dep_canli = parsed_canli
            toplam_canli_gol = ev_canli + dep_canli

            toplam_ornek = len(similar_df)
            over_25_count, btts_count = 0, 0

            for _, row in similar_df.iterrows():
                parsed = parse_score(row.get("SKOR"))
                if not parsed: continue
                h, a = parsed
                if (h + a) > 2.5: over_25_count += 1
                if h >= 1 and a >= 1: btts_count += 1

            pct_over = round((over_25_count / toplam_ornek) * 100, 1)
            pct_btts = round((btts_count / toplam_ornek) * 100, 1)
            dk_int = mac['DAKIKA_INT']

            # 5. Sinyal Mantığı ve Telegram Bildirimi
            signal_type = None
            prob_val = 0.0

            if dk_int >= 60 and toplam_canli_gol < 2 and pct_over >= MIN_PROBABILITY_PCT:
                signal_type = "🔥 CANLI GOL / ÜST BEKLENTİSİ"
                prob_val = pct_over
            elif dk_int >= 65 and (ev_canli == 0 or dep_canli == 0) and pct_btts >= MIN_PROBABILITY_PCT:
                signal_type = "⚽ KG VAR BEKLENTİSİ"
                prob_val = pct_btts

            mac_id = f"{ev}_{dep}_{signal_type}"

            if signal_type and mac_id not in BILDIRIM_GONDERILENLER:
                mesaj = (
                    f"🚨 *YÜKSEK OLASILIKLI CANLI SİNYAL* 🚨\n\n"
                    f"⚽ *Maç:* {ev} vs {dep}\n"
                    f"📊 *Skor:* {skor} | *Dakika:* {dk_str}\n"
                    f"🎯 *Sinyal Türü:* {signal_type}\n"
                    f"📈 *Geçmiş Oran Başarısı:* %{prob_val}\n"
                    f"📊 *Eşleşen Geçmiş Maç:* {toplam_ornek} Adet\n"
                    f"📌 *Açılış Oranları:* MS1: {ms1} | MSX: {msx} | MS2: {ms2}\n\n"
                    f"💡 *Maç önü oranları geçmiş verilerle eşleşti ancak beklenen goller henüz gelmedi!*"
                )
                print(f"🎯 TELEGRAM SİNYALİ GÖNDERİLDİ -> {ev} vs {dep} ({signal_type})\n")
                telegram_mesaj_gonder(mesaj)
                BILDIRIM_GONDERILENLER.add(mac_id)

        except Exception as err:
            print(f"⚠️ Analiz hatası ({ev} vs {dep}): {err}")

    print("=" * 75 + "\n")

# ================= ANA DÖNGÜ =================

if __name__ == "__main__":
    print("🚀 Dinamik Canlı Baraj & Gelişmiş Oran Analiz Botu Başlatıldı.\n")
    while True:
        try:
            canli_ekrani_tara_ve_analiz_et()
        except Exception as e:
            print(f"❌ Ana döngü hatası: {e}")
        
        time.sleep(CHECK_INTERVAL)