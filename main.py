from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
from collections import Counter
from typing import Optional, List, Dict, Any

app = FastAPI(title="Oran Analiz API", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ODDS_COLUMNS = ["MS1", "MSX", "MS2", "UST_2_5", "ALT_2_5"]

def load_data():
    try:
        history_df = pd.read_excel("oranlar.xlsx")
    except Exception:
        history_df = pd.DataFrame()

    try:
        today_df = pd.read_excel("bugun_oranlar.xlsx")
    except Exception:
        today_df = pd.DataFrame()

    return history_df, today_df

def parse_score(score_str: Any) -> Optional[tuple]:
    try:
        if pd.isna(score_str):
            return None
        parts = str(score_str).strip().split("-")
        if len(parts) == 2:
            return int(parts[0]), int(parts[1])
    except Exception:
        pass
    return None

def find_similar_matches(history_df, ms1, msx, ms2, ust, alt, min_matches=5):
    if history_df.empty:
        return pd.DataFrame(), 0.0

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
        if len(filtered) >= min_matches:
            diff = (
                (filtered["MS1"] - ms1).abs() +
                (filtered["MSX"] - msx).abs() +
                (filtered["MS2"] - ms2).abs() +
                (filtered["UST_2_5"] - ust).abs() +
                (filtered["ALT_2_5"] - alt).abs()
            )
            filtered["SIM"] = (1 / (1 + diff)).round(3)
            return filtered, tol
            
    return pd.DataFrame(), 0.30

def get_match_analysis_payload(row, history_df):
    similar_df, tolerance = find_similar_matches(
        history_df,
        row["MS1"], row["MSX"], row["MS2"],
        row["UST_2_5"], row["ALT_2_5"],
        min_matches=5
    )

    if len(similar_df) < 5:
        return None

    home, draw, away, over25, btts = 0, 0, 0, 0, 0
    ev_05, dep_05 = 0, 0
    similar_list = []

    for _, s_row in similar_df.iterrows():
        parsed = parse_score(s_row.get("SKOR"))
        if not parsed:
            continue
        h, a = parsed
        if h > a: home += 1
        elif h == a: draw += 1
        else: away += 1
        if (h + a) > 2.5: over25 += 1
        if h >= 1 and a >= 1: btts += 1
        if h >= 1: ev_05 += 1
        if a >= 1: dep_05 += 1

        similar_list.append({
            "MAC": s_row.get("MAC", "-"),
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

    valid = max(1, len(similar_df))
    scores_list = [str(s) for s in similar_df["SKOR"] if parse_score(s)]
    score_counts = dict(Counter(scores_list))
    
    most_common = Counter(scores_list).most_common(1)
    if most_common:
        top_s, top_count = most_common[0]
        top_score_pct = round((top_count / valid) * 100, 1)
        top_score_str = f"{top_s} (%{top_score_pct})"
    else:
        top_score_pct = 0.0
        top_score_str = "-"

    return {
        "MAC": row.get("MAC", "Bilinmeyen Maç"),
        "MS1_ORAN": row.get("MS1", 0),
        "MSX_ORAN": row.get("MSX", 0),
        "MS2_ORAN": row.get("MS2", 0),
        "UST_ORAN": row.get("UST_2_5", 0),
        "ALT_ORAN": row.get("ALT_2_5", 0),
        "MS1_YUZDE": round((home / valid) * 100, 1),
        "MSX_YUZDE": round((draw / valid) * 100, 1),
        "MS2_YUZDE": round((away / valid) * 100, 1),
        "OVER_YUZDE": round((over25 / valid) * 100, 1),
        "UNDER_YUZDE": round(100 - (over25 / valid) * 100, 1),
        "KG_YUZDE": round((btts / valid) * 100, 1),
        "EV_05_YUZDE": round((ev_05 / valid) * 100, 1),
        "DEP_05_YUZDE": round((dep_05 / valid) * 100, 1),
        "SAMPLE": len(similar_df),
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
        if "HOME_TEAM" in history_df.columns: teams.update(history_df["HOME_TEAM"].dropna().unique())
        if "AWAY_TEAM" in history_df.columns: teams.update(history_df["AWAY_TEAM"].dropna().unique())
    return {
        "history_count": len(history_df),
        "today_count": len(today_df),
        "team_count": len(teams)
    }

@app.get("/api/tum-maclar-list")
def get_tum_maclar_list():
    history_df, _ = load_data()
    if history_df.empty: return {"matches": []}
    return {"matches": history_df["MAC"].dropna().tolist()}

@app.get("/api/yeni-maclar-list")
def get_yeni_maclar_list():
    _, today_df = load_data()
    if today_df.empty: return {"matches": []}
    return {"matches": today_df["MAC"].dropna().tolist()}

@app.get("/api/mac-detay")
def get_mac_detay(mac: str, source: str = "today"):
    history_df, today_df = load_data()
    df = history_df if source == "history" else today_df
    if df.empty: raise HTTPException(status_code=404, detail="Veri bulunamadı")
    
    row = df[df["MAC"] == mac]
    if row.empty: raise HTTPException(status_code=404, detail="Maç bulunamadı")
    
    payload = get_match_analysis_payload(row.iloc[0], history_df)
    if not payload: raise HTTPException(status_code=400, detail="Yetersiz benzer maç verisi")
    return payload

@app.get("/api/bugunun-enleri")
def get_bugunun_enleri():
    history_df, today_df = load_data()
    if today_df.empty: 
        return {
            "ms1": [], "msx": [], "ms2": [], 
            "over": [], "under": [], "kg_var": [], 
            "score_dominance": [], "all": []
        }

    all_analyzed = []
    for idx, row in today_df.iterrows():
        try:
            if any(pd.isna(row[col]) for col in ODDS_COLUMNS): continue
            res = get_match_analysis_payload(row, history_df)
            if res:
                res["ID"] = idx
                all_analyzed.append(res)
        except Exception: continue

    def get_top15(key):
        return sorted(all_analyzed, key=lambda x: x[key], reverse=True)[:15]

    return {
        "ms1": get_top15("MS1_YUZDE"),
        "msx": get_top15("MSX_YUZDE"),
        "ms2": get_top15("MS2_YUZDE"),
        "over": get_top15("OVER_YUZDE"),
        "under": get_top15("UNDER_YUZDE"),
        "kg_var": get_top15("KG_YUZDE"),
        "score_dominance": get_top15("TOP_SCORE_PCT"),
        "all": all_analyzed
    }

@app.get("/api/takimlar")
def get_takimlar(filter: str = "win"):
    history_df, _ = load_data()
    if history_df.empty: return {"teams": []}

    team_stats = {}

    for _, row in history_df.iterrows():
        parsed = parse_score(row.get("SKOR"))
        if not parsed: continue
        h_score, a_score = parsed
        total_goals = h_score + a_score

        home_team = row.get("HOME_TEAM")
        away_team = row.get("AWAY_TEAM")

        if pd.notna(home_team) and str(home_team).strip() != "":
            ht = str(home_team).strip()
            if ht not in team_stats:
                team_stats[ht] = {
                    "name": ht, "total_matches": 0, "wins": 0, 
                    "total_goals": 0, "home_matches": 0, "home_goals": 0, 
                    "away_matches": 0, "away_goals": 0
                }
            team_stats[ht]["total_matches"] += 1
            team_stats[ht]["home_matches"] += 1
            team_stats[ht]["total_goals"] += total_goals
            team_stats[ht]["home_goals"] += total_goals
            if h_score > a_score: team_stats[ht]["wins"] += 1

        if pd.notna(away_team) and str(away_team).strip() != "":
            at = str(away_team).strip()
            if at not in team_stats:
                team_stats[at] = {
                    "name": at, "total_matches": 0, "wins": 0, 
                    "total_goals": 0, "home_matches": 0, "home_goals": 0, 
                    "away_matches": 0, "away_goals": 0
                }
            team_stats[at]["total_matches"] += 1
            team_stats[at]["away_matches"] += 1
            team_stats[at]["total_goals"] += total_goals
            team_stats[at]["away_goals"] += total_goals
            if a_score > h_score: team_stats[at]["wins"] += 1

    qualified_teams = []
    for t_name, stats in team_stats.items():
        if stats["total_matches"] >= 3:
            win_rate = round((stats["wins"] / stats["total_matches"]) * 100, 1)
            avg_goals = round(stats["total_goals"] / stats["total_matches"], 2)
            home_avg_goals = round(stats["home_goals"] / max(1, stats["home_matches"]), 2)
            away_avg_goals = round(stats["away_goals"] / max(1, stats["away_matches"]), 2)

            qualified_teams.append({
                "name": stats["name"],
                "total_matches": stats["total_matches"],
                "win_rate": win_rate,
                "avg_goals": avg_goals,
                "home_avg_goals": home_avg_goals,
                "away_avg_goals": away_avg_goals
            })

    if filter == "gollu":
        qualified_teams.sort(key=lambda x: x["avg_goals"], reverse=True)
    elif filter == "home_gollu":
        qualified_teams.sort(key=lambda x: x["home_avg_goals"], reverse=True)
    elif filter == "away_gollu":
        qualified_teams.sort(key=lambda x: x["away_avg_goals"], reverse=True)
    else:
        qualified_teams.sort(key=lambda x: x["win_rate"], reverse=True)

    return {"teams": qualified_teams}