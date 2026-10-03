from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from collections import Counter
from typing import Optional, Any
from sqlalchemy import create_engine
import time

app = FastAPI(title="Oran Analiz API", version="6.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_URL = "postgresql://postgres:KatarinaRostova67@db.xqhdhwdgitksemfidsdi.supabase.co:5432/postgres"
engine = create_engine(DB_URL)

ODDS_COLUMNS = ["MS1", "MSX", "MS2", "UST_2_5", "ALT_2_5"]

MIN_SIMILAR_MATCHES = 7
SIMILARITY_TOLERANCE = 0.05
MIN_TEAM_MATCHES = 7

CACHE_DATA = {
    "history_df": pd.DataFrame(),
    "today_df": pd.DataFrame(),
    "last_updated": 0
}
CACHE_TTL = 300


def load_data(force_refresh: bool = False):
    now = time.time()
    
    if not force_refresh and not CACHE_DATA["history_df"].empty and (now - CACHE_DATA["last_updated"] < CACHE_TTL):
        return CACHE_DATA["history_df"], CACHE_DATA["today_df"]

    try:
        history_df = pd.read_sql("SELECT * FROM oranlar", engine)
        history_df.columns = [str(c).upper().strip() for c in history_df.columns]
    except Exception as e:
        print(f"History okuma hatasi: {e}")
        history_df = pd.DataFrame()

    try:
        today_df = pd.read_sql("SELECT * FROM bugun_oranlar", engine)
        today_df.columns = [str(c).upper().strip() for c in today_df.columns]
    except Exception as e:
        print(f"Today okuma hatasi: {e}")
        today_df = pd.DataFrame()

    for df in [history_df, today_df]:
        if not df.empty:
            for col in ODDS_COLUMNS:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

    CACHE_DATA["history_df"] = history_df
    CACHE_DATA["today_df"] = today_df
    CACHE_DATA["last_updated"] = now

    return history_df, today_df


@app.get("/api/clear-cache")
@app.get("/api/cache-clear")
def clear_cache():
    load_data(force_refresh=True)
    return {"status": "success", "message": "Önbellek temizlendi ve güncellendi."}


def parse_score(score_str: Any) -> Optional[tuple]:
    try:
        if pd.isna(score_str):
            return None
        parts = str(score_str).strip().split("-")
        if len(parts) != 2:
            return None
        return int(parts[0].strip()), int(parts[1].strip())
    except Exception:
        return None


def format_saat(saat_val: Any) -> str:
    if pd.isna(saat_val):
        return ""
    st = str(saat_val).strip()
    if len(st) >= 5 and ":" in st:
        return st[:5]
    return st


def find_similar_matches(history_df, ms1, msx, ms2, ust, alt, min_matches=MIN_SIMILAR_MATCHES):
    if history_df.empty:
        return pd.DataFrame(), SIMILARITY_TOLERANCE

    try:
        values = [ms1, msx, ms2, ust, alt]
        if any(pd.isna(v) for v in values):
            return pd.DataFrame(), SIMILARITY_TOLERANCE

        for col in ODDS_COLUMNS:
            if col not in history_df.columns:
                return pd.DataFrame(), SIMILARITY_TOLERANCE

        condition = (
            history_df["MS1"].between(ms1 - SIMILARITY_TOLERANCE, ms1 + SIMILARITY_TOLERANCE) &
            history_df["MSX"].between(msx - SIMILARITY_TOLERANCE, msx + SIMILARITY_TOLERANCE) &
            history_df["MS2"].between(ms2 - SIMILARITY_TOLERANCE, ms2 + SIMILARITY_TOLERANCE) &
            history_df["UST_2_5"].between(ust - SIMILARITY_TOLERANCE, ust + SIMILARITY_TOLERANCE) &
            history_df["ALT_2_5"].between(alt - SIMILARITY_TOLERANCE, alt + SIMILARITY_TOLERANCE)
        )

        filtered = history_df[condition].copy()
        if len(filtered) < min_matches:
            return pd.DataFrame(), SIMILARITY_TOLERANCE

        diff = (
            (filtered["MS1"] - ms1).abs() +
            (filtered["MSX"] - msx).abs() +
            (filtered["MS2"] - ms2).abs() +
            (filtered["UST_2_5"] - ust).abs() +
            (filtered["ALT_2_5"] - alt).abs()
        )

        filtered["SIM"] = (1 / (1 + diff)).round(3)
        filtered = filtered.sort_values(by="SIM", ascending=False)
        return filtered, SIMILARITY_TOLERANCE
    except Exception:
        return pd.DataFrame(), SIMILARITY_TOLERANCE


def get_match_analysis_payload(row, history_df, min_matches=MIN_SIMILAR_MATCHES):
    similar_df, tolerance = find_similar_matches(
        history_df, row.get("MS1"), row.get("MSX"), row.get("MS2"), row.get("UST_2_5"), row.get("ALT_2_5"), min_matches=min_matches
    )

    if len(similar_df) < min_matches:
        return None

    home, draw, away, over25, btts, ev_05, dep_05 = 0, 0, 0, 0, 0, 0, 0
    similar_list = []
    valid_scores = []

    for _, s_row in similar_df.iterrows():
        parsed = parse_score(s_row.get("SKOR"))
        if not parsed:
            continue

        h, a = parsed
        valid_scores.append(f"{h}-{a}")

        if h > a: home += 1
        elif h == a: draw += 1
        else: away += 1

        if h + a > 2.5: over25 += 1
        if h >= 1 and a >= 1: btts += 1
        if h >= 1: ev_05 += 1
        if a >= 1: dep_05 += 1

        similar_list.append({
            "MAC": s_row.get("MAC", "-"),
            "SAAT": format_saat(s_row.get("SAAT")),
            "SKOR": str(s_row.get("SKOR", "-")),
            "MS1": s_row.get("MS1", 0),
            "MSX": s_row.get("MSX", 0),
            "MS2": s_row.get("MS2", 0),
            "UST_2_5": s_row.get("UST_2_5", 0),
            "ALT_2_5": s_row.get("ALT_2_5", 0),
            "HOME_TEAM": s_row.get("HOME_TEAM", "-"),
            "AWAY_TEAM": s_row.get("AWAY_TEAM", "-"),
            "SIM": s_row.get("SIM", 0)
        })

    valid = len(valid_scores)
    if valid < min_matches:
        return None

    score_counts = dict(Counter(valid_scores))
    most_common = Counter(valid_scores).most_common(1)

    if most_common:
        top_score, top_count = most_common[0]
        top_score_pct = round((top_count / valid) * 100, 1)
        top_score_str = f"{top_score} (%{top_score_pct})"
    else:
        top_score_pct = 0.0
        top_score_str = "-"

    saat_val = format_saat(row.get("SAAT"))
    raw_mac = str(row.get("MAC", "Bilinmeyen Maç")).strip()
    display_mac = f"[{saat_val}] {raw_mac}" if saat_val else raw_mac

    return {
        "MAC": display_mac,
        "RAW_MAC": raw_mac,
        "SAAT": saat_val,
        "MS1_ORAN": row.get("MS1", 0),
        "MSX_ORAN": row.get("MSX", 0),
        "MS2_ORAN": row.get("MS2", 0),
        "UST_ORAN": row.get("UST_2_5", 0),
        "ALT_ORAN": row.get("ALT_2_5", 0),
        "MS1_YUZDE": round((home / valid) * 100, 1),
        "MSX_YUZDE": round((draw / valid) * 100, 1),
        "MS2_YUZDE": round((away / valid) * 100, 1),
        "OVER_YUZDE": round((over25 / valid) * 100, 1),
        "UNDER_YUZDE": round(100 - ((over25 / valid) * 100), 1),
        "KG_YUZDE": round((btts / valid) * 100, 1),
        "EV_05_YUZDE": round((ev_05 / valid) * 100, 1),
        "DEP_05_YUZDE": round((dep_05 / valid) * 100, 1),
        "SAMPLE": valid,
        "TOP_SCORE": top_score_str,
        "TOP_SCORE_PCT": top_score_pct,
        "SCORE_COUNTS": score_counts,
        "TOLERANCE": tolerance,
        "SIMILAR_MATCHES": similar_list
    }


@app.get("/api/stats")
def get_stats():
    history_df, today_df = load_data()
    teams = set()

    if not history_df.empty:
        if "HOME_TEAM" in history_df.columns:
            teams.update(history_df["HOME_TEAM"].dropna().unique())
        if "AWAY_TEAM" in history_df.columns:
            teams.update(history_df["AWAY_TEAM"].dropna().unique())

    return {
        "history_count": len(history_df),
        "today_count": len(today_df),
        "team_count": len(teams),
        "min_similar_matches": MIN_SIMILAR_MATCHES,
        "tolerance": SIMILARITY_TOLERANCE,
        "min_team_matches": MIN_TEAM_MATCHES
    }


@app.get("/api/tum-maclar-list")
@app.get("/api/tum-maclar")
def get_tum_maclar_list():
    history_df, _ = load_data()
    if history_df.empty or "MAC" not in history_df.columns:
        return {"matches": []}

    matches = []
    for idx, row in history_df.iterrows():
        mac = str(row.get("MAC", "")).strip()
        if not mac or mac.lower() in ["nan", "none", "null"]:
            continue
        saat = format_saat(row.get("SAAT"))
        display_name = f"[{saat}] {mac}" if saat else mac
        matches.append(display_name)

    return {"matches": matches, "data": matches}


@app.get("/api/yeni-maclar-list")
@app.get("/api/bugun-oranlar")
def get_yeni_maclar_list():
    try:
        df = pd.read_sql("SELECT * FROM bugun_oranlar", engine)
        
        if df.empty:
            return {"matches": [], "status": "empty_table", "message": "bugun_oranlar tablosu boş"}
            
        df.columns = [str(c).upper().strip() for c in df.columns]
        
        matches_list = []
        matches_obj_list = []

        for idx, row in df.iterrows():
            mac_val = row.get("MAC")
            if pd.isna(mac_val):
                continue
            
            mac = str(mac_val).strip()
            if not mac or mac.lower() in ["nan", "none", "null"]:
                continue

            saat = str(row.get("SAAT", "")).strip()
            if len(saat) >= 5 and ":" in saat:
                saat = saat[:5]

            display_name = f"[{saat}] {mac}" if saat else mac
            
            matches_list.append(display_name)
            matches_obj_list.append({
                "id": int(idx),
                "mac": mac,
                "display": display_name,
                "saat": saat,
                "ms1": row.get("MS1"),
                "msx": row.get("MSX"),
                "ms2": row.get("MS2")
            })

        return {
            "matches": matches_list,
            "matches_obj": matches_obj_list,
            "data": matches_list,
            "count": len(matches_list)
        }
    except Exception as e:
        return {"matches": [], "error": str(e), "status": "exception"}


@app.get("/api/mac-detay")
def get_mac_detay(mac: str, source: str = "today"):
    history_df, today_df = load_data()
    df = history_df if source == "history" else today_df

    if df.empty or "MAC" not in df.columns:
        raise HTTPException(status_code=404, detail="Veri bulunamadı")

    search_mac = mac.strip()
    if search_mac.startswith("[") and "]" in search_mac:
        search_mac = search_mac.split("]", 1)[1].strip()

    row = df[df["MAC"].astype(str).str.strip() == search_mac]
    if row.empty:
        row = df[df["MAC"].astype(str) == str(mac)]

    if row.empty:
        raise HTTPException(status_code=404, detail="Maç bulunamadı")

    payload = get_match_analysis_payload(row.iloc[0], history_df, min_matches=1)
    if not payload:
        raise HTTPException(status_code=400, detail="Benzer maç bulunamadı.")

    return payload


@app.get("/api/bugunun-enleri")
def get_bugunun_enleri():
    history_df, today_df = load_data()

    empty_response = {
        "ms1": [], "msx": [], "ms2": [], "over": [], "under": [],
        "kg_var": [], "score_dominance": [], "all": [],
        "min_matches": MIN_SIMILAR_MATCHES, "tolerance": SIMILARITY_TOLERANCE
    }

    if today_df.empty:
        return empty_response

    all_analyzed = []

    for idx, row in today_df.iterrows():
        try:
            if any(col not in row.index or pd.isna(row[col]) for col in ODDS_COLUMNS):
                continue

            result = get_match_analysis_payload(row, history_df, min_matches=MIN_SIMILAR_MATCHES)

            if result:
                result["ID"] = int(idx)
                all_analyzed.append(result)
        except Exception:
            continue

    def get_top15(key):
        return sorted(all_analyzed, key=lambda x: x.get(key, 0), reverse=True)[:15]

    return {
        "ms1": get_top15("MS1_YUZDE"),
        "msx": get_top15("MSX_YUZDE"),
        "ms2": get_top15("MS2_YUZDE"),
        "over": get_top15("OVER_YUZDE"),
        "under": get_top15("UNDER_YUZDE"),
        "kg_var": get_top15("KG_YUZDE"),
        "score_dominance": get_top15("TOP_SCORE_PCT"),
        "all": all_analyzed,
        "min_matches": MIN_SIMILAR_MATCHES,
        "tolerance": SIMILARITY_TOLERANCE
    }