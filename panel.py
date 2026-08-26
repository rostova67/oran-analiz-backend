# =====================================================
# GELİŞMİŞ ORAN ANALİZ PANELİ
# TAKIM + ORAN BENZERLİĞİ + EV/DEP 0.5 ÜST
# FULL VERSION
# =====================================================

import os
import streamlit as st
import pandas as pd
import numpy as np

from collections import Counter


# =====================================================
# SAYFA AYARLARI
# =====================================================

st.set_page_config(
    page_title="ORAN ANALİZ PANELİ",
    page_icon="📊",
    layout="wide"
)


# =====================================================
# CSS
# =====================================================

st.markdown("""
<style>

.stApp {
    background-color: #0f172a;
}

h1, h2, h3, h4, h5, p, span, div, label {
    color: white !important;
}

section[data-testid="stSidebar"] {
    background-color: #111827;
}

.stRadio label {
    background-color: #1e293b;
    padding: 15px !important;
    border-radius: 14px;
    font-size: 18px !important;
    font-weight: bold;
    border: 1px solid #334155;
    margin-bottom: 8px;
}

.score-box {
    background-color: #1e293b;
    padding: 18px;
    border-radius: 15px;
    border: 1px solid #334155;
    margin-bottom: 12px;
    text-align: center;
}

.odds-box {
    background-color: #1e293b;
    padding: 16px;
    border-radius: 14px;
    border: 2px dashed #38bdf8;
    margin-bottom: 20px;
}

.top-card {
    background-color: #1e293b;
    padding: 18px;
    border-radius: 14px;
    border-left: 5px solid #38bdf8;
    margin-bottom: 14px;
}

.green {
    color: #22c55e !important;
    font-size: 27px;
    font-weight: bold;
}

.red {
    color: #ef4444 !important;
    font-size: 27px;
    font-weight: bold;
}

.yellow {
    color: #facc15 !important;
    font-size: 27px;
    font-weight: bold;
}

.blue {
    color: #38bdf8 !important;
    font-size: 27px;
    font-weight: bold;
}

.small-text {
    font-size: 14px;
    color: #cbd5e1 !important;
}

</style>
""", unsafe_allow_html=True)


# =====================================================
# SABİTLER
# =====================================================

ODDS_COLUMNS = [
    "MS1",
    "MSX",
    "MS2",
    "UST_2_5",
    "ALT_2_5"
]

MIN_TEAM_MATCHES = 3


# =====================================================
# YARDIMCI FONKSİYONLAR
# =====================================================

def clean_team_name(value):
    if pd.isna(value):
        return ""

    return str(value).strip()


def parse_score(score):
    """
    2-1
    2 - 1
    gibi skorları okur.
    """

    if pd.isna(score):
        return None

    text = str(score).strip()

    if "-" not in text:
        return None

    try:
        parts = text.split("-")

        if len(parts) != 2:
            return None

        home_goals = int(
            parts[0].strip()
        )

        away_goals = int(
            parts[1].strip()
        )

        return home_goals, away_goals

    except Exception:
        return None


def parse_teams_from_mac(mac):
    """
    MAC sütunundan takım isimlerini çıkarmaya çalışır.

    Desteklenen:
        Takım A - Takım B
        Takım A vs Takım B
        Takım A v Takım B
    """

    if pd.isna(mac):
        return "", ""

    text = str(mac).strip()

    separators = [
        " vs ",
        " VS ",
        " v ",
        " V ",
        " - ",
        " – ",
        " — "
    ]

    for separator in separators:

        if separator in text:

            parts = text.split(
                separator,
                1
            )

            if len(parts) == 2:

                home = parts[0].strip()
                away = parts[1].strip()

                if home and away:
                    return home, away

    return "", ""


# =====================================================
# EXCEL DOSYASINI OKUMA
# DOSYA DEĞİŞMEDİKÇE TEKRAR OKUMAZ
# =====================================================

@st.cache_data(
    ttl=600,
    show_spinner=False
)
def read_excel_cached(
    file_name,
    modified_time
):

    try:
        return pd.read_excel(
            file_name
        )

    except Exception:
        return pd.DataFrame()


# =====================================================
# VERİ YÜKLEME
# =====================================================

@st.cache_data(
    ttl=600,
    show_spinner=False
)
def load_data():

    history_file = "oranlar.xlsx"
    today_file = "bugun_oranlar.xlsx"

    history_mtime = (
        os.path.getmtime(history_file)
        if os.path.exists(history_file)
        else 0
    )

    today_mtime = (
        os.path.getmtime(today_file)
        if os.path.exists(today_file)
        else 0
    )

    history_df = read_excel_cached(
        history_file,
        history_mtime
    )

    today_df = read_excel_cached(
        today_file,
        today_mtime
    )

    # -------------------------------------------------
    # UST / ALT isimlerini standartlaştır
    # -------------------------------------------------

    for df in [
        history_df,
        today_df
    ]:

        if df.empty:
            continue

        if (
            "UST" in df.columns
            and
            "UST_2_5" not in df.columns
        ):
            df["UST_2_5"] = df["UST"]

        if (
            "ALT" in df.columns
            and
            "ALT_2_5" not in df.columns
        ):
            df["ALT_2_5"] = df["ALT"]

    # -------------------------------------------------
    # Oranları sayıya çevir
    # -------------------------------------------------

    for col in ODDS_COLUMNS:

        if (
            not history_df.empty
            and
            col in history_df.columns
        ):

            history_df[col] = pd.to_numeric(
                history_df[col],
                errors="coerce"
            )

        if (
            not today_df.empty
            and
            col in today_df.columns
        ):

            today_df[col] = pd.to_numeric(
                today_df[col],
                errors="coerce"
            )

    # -------------------------------------------------
    # Sadece SKORU OLAN GEÇMİŞ MAÇLAR
    # -------------------------------------------------

    if (
        not history_df.empty
        and
        "SKOR" in history_df.columns
    ):

        history_scored = history_df[
            history_df["SKOR"].notna()
        ].copy()

        history_scored = history_scored[
            history_scored["SKOR"]
            .astype(str)
            .str.contains(
                "-",
                regex=False
            )
        ].copy()

    else:

        history_scored = pd.DataFrame()

    # -------------------------------------------------
    # Takımları MAC'tan çıkar
    # -------------------------------------------------

    for df in [
        history_scored,
        today_df
    ]:

        if df.empty:
            continue

        homes = []
        aways = []

        for mac in df["MAC"]:

            home, away = parse_teams_from_mac(
                mac
            )

            homes.append(
                home
            )

            aways.append(
                away
            )

        df["HOME_TEAM"] = homes
        df["AWAY_TEAM"] = aways

    return (
        history_df,
        today_df,
        history_scored
    )


history_df, today_df, history_scored = load_data()


# =====================================================
# TAKIM MAÇLARINI HAZIRLA
# =====================================================

@st.cache_data(
    ttl=600,
    show_spinner=False
)
def build_team_database(
    scored_df
):

    team_matches = {}

    if scored_df.empty:
        return team_matches

    for _, row in scored_df.iterrows():

        home = clean_team_name(
            row.get(
                "HOME_TEAM",
                ""
            )
        )

        away = clean_team_name(
            row.get(
                "AWAY_TEAM",
                ""
            )
        )

        score = parse_score(
            row.get(
                "SKOR",
                ""
            )
        )

        if (
            not home
            or
            not away
            or
            not score
        ):
            continue

        home_goals, away_goals = score

        # ---------------------------------------------
        # EV TAKIMI
        # ---------------------------------------------

        if home not in team_matches:
            team_matches[home] = []

        team_matches[home].append(
            {
                "MAC": row.get(
                    "MAC",
                    ""
                ),
                "TEAM": home,
                "OPPONENT": away,
                "VENUE": "EV",
                "TEAM_GOALS": home_goals,
                "OPP_GOALS": away_goals,
                "TOTAL_GOALS":
                    home_goals
                    +
                    away_goals,
                "WIN":
                    home_goals > away_goals,
                "DRAW":
                    home_goals == away_goals,
                "LOSS":
                    home_goals < away_goals,
                "TEAM_SCORED":
                    home_goals >= 1,
                "OPP_SCORED":
                    away_goals >= 1,
                "BTTS":
                    home_goals >= 1
                    and
                    away_goals >= 1
            }
        )

        # ---------------------------------------------
        # DEPLASMAN TAKIMI
        # ---------------------------------------------

        if away not in team_matches:
            team_matches[away] = []

        team_matches[away].append(
            {
                "MAC": row.get(
                    "MAC",
                    ""
                ),
                "TEAM": away,
                "OPPONENT": home,
                "VENUE": "DEP",
                "TEAM_GOALS": away_goals,
                "OPP_GOALS": home_goals,
                "TOTAL_GOALS":
                    home_goals
                    +
                    away_goals,
                "WIN":
                    away_goals > home_goals,
                "DRAW":
                    away_goals == home_goals,
                "LOSS":
                    away_goals < home_goals,
                "TEAM_SCORED":
                    away_goals >= 1,
                "OPP_SCORED":
                    home_goals >= 1,
                "BTTS":
                    home_goals >= 1
                    and
                    away_goals >= 1
            }
        )

    return team_matches


team_matches = build_team_database(
    history_scored
)


# =====================================================
# TAKIM İSTATİSTİĞİ
# =====================================================

def calculate_team_stats(
    team_matches,
    team
):

    matches = team_matches.get(
        team,
        []
    )

    if len(matches) < MIN_TEAM_MATCHES:
        return None

    df = pd.DataFrame(
        matches
    )

    total = len(df)

    points = (
        df["WIN"].sum() * 3
        +
        df["DRAW"].sum()
    )

    return {
        "matches": total,

        "points": int(
            points
        ),

        "ppm": round(
            points / total,
            2
        ),

        "win_pct": round(
            df["WIN"].mean() * 100,
            1
        ),

        "draw_pct": round(
            df["DRAW"].mean() * 100,
            1
        ),

        "loss_pct": round(
            df["LOSS"].mean() * 100,
            1
        ),

        "gf_avg": round(
            df["TEAM_GOALS"].mean(),
            2
        ),

        "ga_avg": round(
            df["OPP_GOALS"].mean(),
            2
        ),

        "team_score_pct": round(
            df["TEAM_SCORED"].mean() * 100,
            1
        ),

        "opponent_score_pct": round(
            df["OPP_SCORED"].mean() * 100,
            1
        ),

        "btts_pct": round(
            df["BTTS"].mean() * 100,
            1
        ),

        "over25_pct": round(
            (
                df["TOTAL_GOALS"] >= 3
            ).mean() * 100,
            1
        ),

        "under25_pct": round(
            (
                df["TOTAL_GOALS"] <= 2
            ).mean() * 100,
            1
        ),

        "home_matches": int(
            (
                df["VENUE"] == "EV"
            ).sum()
        ),

        "away_matches": int(
            (
                df["VENUE"] == "DEP"
            ).sum()
        )
    }


# =====================================================
# TAKIM LİSTESİ
# =====================================================

def get_valid_teams(
    team_matches
):

    result = []

    for team, matches in team_matches.items():

        if len(matches) >= MIN_TEAM_MATCHES:

            result.append(
                team
            )

    return sorted(
        result
    )


valid_teams = get_valid_teams(
    team_matches
)


# =====================================================
# ORAN BENZERLİĞİ
# BUGÜNKÜ MAÇI GEÇMİŞ MAÇLARLA KARŞILAŞTIR
# =====================================================

def find_similar_matches(
    current_ms1,
    current_msx,
    current_ms2,
    current_ust,
    current_alt,
    min_matches=3
):

    if history_scored.empty:
        return pd.DataFrame(), 0

    target = np.array(
        [
            current_ms1,
            current_msx,
            current_ms2,
            current_ust,
            current_alt
        ],
        dtype=float
    )

    candidates = []

    # ---------------------------------------------
    # Tolerans sırası
    # ---------------------------------------------

    tolerances = [
        0.10,
        0.15,
        0.20,
        0.25,
        0.30,
        0.35
    ]

    for tolerance in tolerances:

        candidates = []

        for _, row in history_scored.iterrows():

            try:

                values = [
                    float(row["MS1"]),
                    float(row["MSX"]),
                    float(row["MS2"]),
                    float(row["UST_2_5"]),
                    float(row["ALT_2_5"])
                ]

                if any(
                    pd.isna(v)
                    for v in values
                ):
                    continue

                differences = np.abs(
                    np.array(values)
                    -
                    target
                )

                if np.all(
                    differences
                    <=
                    tolerance
                ):

                    similarity = float(
                        differences.sum()
                    )

                    result = row.to_dict()

                    result["SIM"] = round(
                        similarity,
                        4
                    )

                    candidates.append(
                        result
                    )

            except Exception:
                continue

        if len(candidates) >= min_matches:

            return (
                pd.DataFrame(
                    candidates
                ).sort_values(
                    "SIM"
                ),
                tolerance
            )

    if candidates:

        return (
            pd.DataFrame(
                candidates
            ).sort_values(
                "SIM"
            ),
            tolerances[-1]
        )

    return (
        pd.DataFrame(),
        tolerances[-1]
    )


# =====================================================
# EV 0.5 / DEP 0.5 ANALİZİ
# =====================================================

def calculate_goal_market_from_similar(
    similar_df
):

    if (
        similar_df is None
        or
        similar_df.empty
    ):

        return {
            "home05": 0,
            "away05": 0,
            "sample": 0,
            "home_scored": 0,
            "away_scored": 0,
            "btts": 0,
            "over25": 0
        }

    home_scored = 0
    away_scored = 0
    btts = 0
    over25 = 0

    valid = 0

    for _, row in similar_df.iterrows():

        score = parse_score(
            row.get(
                "SKOR",
                ""
            )
        )

        if not score:
            continue

        home_goals, away_goals = score

        valid += 1

        if home_goals >= 1:
            home_scored += 1

        if away_goals >= 1:
            away_scored += 1

        if (
            home_goals >= 1
            and
            away_goals >= 1
        ):
            btts += 1

        if (
            home_goals
            +
            away_goals
            >= 3
        ):
            over25 += 1

    if valid == 0:

        return {
            "home05": 0,
            "away05": 0,
            "sample": 0,
            "home_scored": 0,
            "away_scored": 0,
            "btts": 0,
            "over25": 0
        }

    return {
        "home05": round(
            home_scored
            /
            valid
            *
            100,
            1
        ),

        "away05": round(
            away_scored
            /
            valid
            *
            100,
            1
        ),

        "sample": valid,

        "home_scored":
            home_scored,

        "away_scored":
            away_scored,

        "btts": round(
            btts
            /
            valid
            *
            100,
            1
        ),

        "over25": round(
            over25
            /
            valid
            *
            100,
            1
        )
    }


# =====================================================
# TAKIM İÇİN BENZER MAÇLAR
# SADECE TAKIMIN KENDİ OYNADIĞI MAÇLAR
# =====================================================

def get_team_similar_history(
    team,
    current_ms1,
    current_msx,
    current_ms2,
    current_ust,
    current_alt,
    min_matches=3
):

    if team not in team_matches:
        return pd.DataFrame(), 0

    team_history = team_matches[
        team
    ]

    if len(team_history) < MIN_TEAM_MATCHES:
        return pd.DataFrame(), 0

    # -------------------------------------------------
    # Önce takımın geçmiş MAC'lerini bul
    # -------------------------------------------------

    team_mac_set = set(
        str(item["MAC"]).strip()
        for item in team_history
    )

    # -------------------------------------------------
    # Global oran geçmişinden sadece bu takımın
    # maçlarını seç
    # -------------------------------------------------

    team_history_rows = history_scored[
        history_scored["MAC"]
        .astype(str)
        .str.strip()
        .isin(
            team_mac_set
        )
    ].copy()

    if team_history_rows.empty:

        return (
            pd.DataFrame(),
            0
        )

    target = np.array(
        [
            current_ms1,
            current_msx,
            current_ms2,
            current_ust,
            current_alt
        ],
        dtype=float
    )

    tolerances = [
        0.10,
        0.15,
        0.20,
        0.25,
        0.30,
        0.35
    ]

    for tolerance in tolerances:

        found = []

        for _, row in team_history_rows.iterrows():

            try:

                values = np.array(
                    [
                        float(row["MS1"]),
                        float(row["MSX"]),
                        float(row["MS2"]),
                        float(row["UST_2_5"]),
                        float(row["ALT_2_5"])
                    ],
                    dtype=float
                )

                if np.isnan(
                    values
                ).any():

                    continue

                diff = np.abs(
                    values
                    -
                    target
                )

                if np.all(
                    diff <= tolerance
                ):

                    result = row.to_dict()

                    result["SIM"] = round(
                        float(diff.sum()),
                        4
                    )

                    found.append(
                        result
                    )

            except Exception:
                continue

        if len(found) >= min_matches:

            return (
                pd.DataFrame(
                    found
                ).sort_values(
                    "SIM"
                ),
                tolerance
            )

        if found:

            best_found = pd.DataFrame(
                found
            )

        else:

            best_found = pd.DataFrame()

    return (
        best_found,
        tolerances[-1]
    )


# =====================================================
# BUGÜNÜN EV 0.5 / DEP 0.5 ANALİZLERİ
# =====================================================

@st.cache_data(
    ttl=600,
    show_spinner=False
)
def calculate_today_goal_markets():

    if today_df.empty:
        return pd.DataFrame()

    results = []

    for _, row in today_df.iterrows():

        try:

            if any(
                pd.isna(
                    row[col]
                )
                for col in ODDS_COLUMNS
            ):
                continue

            mac = str(
                row["MAC"]
            ).strip()

            home = clean_team_name(
                row.get(
                    "HOME_TEAM",
                    ""
                )
            )

            away = clean_team_name(
                row.get(
                    "AWAY_TEAM",
                    ""
                )
            )

            if not home or not away:
                continue

            similar_df, tolerance = find_similar_matches(
                row["MS1"],
                row["MSX"],
                row["MS2"],
                row["UST_2_5"],
                row["ALT_2_5"],
                min_matches=3
            )

            market = calculate_goal_market_from_similar(
                similar_df
            )

            results.append(
                {
                    "MAC": mac,
                    "HOME": home,
                    "AWAY": away,

                    "MS1": row["MS1"],
                    "MSX": row["MSX"],
                    "MS2": row["MS2"],

                    "UST_2_5":
                        row["UST_2_5"],

                    "ALT_2_5":
                        row["ALT_2_5"],

                    "EV_0_5":
                        market["home05"],

                    "DEP_0_5":
                        market["away05"],

                    "KG_VAR":
                        market["btts"],

                    "OVER_2_5":
                        market["over25"],

                    "SAMPLE":
                        market["sample"],

                    "EV_GOL_ADET":
                        market["home_scored"],

                    "DEP_GOL_ADET":
                        market["away_scored"],

                    "TOLERANCE":
                        tolerance
                }
            )

        except Exception:
            continue

    if not results:
        return pd.DataFrame()

    return pd.DataFrame(
        results
    )


today_goal_markets = calculate_today_goal_markets()


# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.title(
    "MENÜ"
)

if st.sidebar.button(
    "🔄 Verileri Yenile",
    use_container_width=True
):

    st.cache_data.clear()
    st.rerun()


page = st.sidebar.radio(
    "Sayfa Seçimi",
    [
        "Tüm Maçlar Seç",
        "Yeni Maçlar Seç",
        "🔥 BUGÜNÜN ENLERİ",
        "👥 TAKIM DETAY"
    ]
)

st.sidebar.markdown("---")

st.sidebar.markdown(
    f"📊 **Skorlu Analiz Havuzu:** `{len(history_scored)} Maç`"
)

st.sidebar.markdown(
    f"📅 **Bugün Seçilecek Maçlar:** `{len(today_df)} Maç`"
)

st.sidebar.markdown(
    f"👥 **Analiz Edilebilir Takım:** `{len(valid_teams)}`"
)

# =====================================================
# SAYFA 1
# TÜM MAÇLAR
# =====================================================

if page == "Tüm Maçlar Seç":

    st.title(
        "📂 GEÇMİŞ TÜM MAÇLAR VERİTABANI ANALİZİ"
    )

    if (
        history_scored.empty
        or
        "MAC" not in history_scored.columns
    ):

        st.error(
            "oranlar.xlsx dosyasında skoru girilmiş geçerli maç bulunamadı!"
        )

        st.stop()

    all_matches = (
        history_scored["MAC"]
        .dropna()
        .unique()
        .tolist()
    )

    selected_hist = st.selectbox(
        "Geçmiş Arşivden Bir Maç Seçin",
        ["MAÇ SEÇİNİZ"] + all_matches
    )

    if selected_hist == "MAÇ SEÇİNİZ":

        st.info(
            "Analiz detaylarını görüntülemek için yukarıdan bir maç seçin."
        )

        st.stop()

    row = history_scored[
        history_scored["MAC"]
        ==
        selected_hist
    ].iloc[0]

    analysis_df, tolerance = find_similar_matches(
        row["MS1"],
        row["MSX"],
        row["MS2"],
        row["UST_2_5"],
        row["ALT_2_5"],
        min_matches=4
    )

    market = calculate_goal_market_from_similar(
        analysis_df
    )

    st.subheader(
        f"📊 {selected_hist} - Maç Analiz Raporu"
    )

    st.write(
        f"**Orijinal Skor:** {row.get('SKOR', '-')}"
        f" | **Tolerans:** {tolerance}"
        f" | **Benzer Maç:** {len(analysis_df)}"
    )

    st.markdown(
        f"""
        <div class='odds-box'>
        📊 SEÇİLEN MAÇIN ORANLARI
        <br><br>
        MS1: {row['MS1']}
        &nbsp;&nbsp;|&nbsp;&nbsp;
        MSX: {row['MSX']}
        &nbsp;&nbsp;|&nbsp;&nbsp;
        MS2: {row['MS2']}
        &nbsp;&nbsp;|&nbsp;&nbsp;
        ÜST: {row['UST_2_5']}
        &nbsp;&nbsp;|&nbsp;&nbsp;
        ALT: {row['ALT_2_5']}
        </div>
        """,
        unsafe_allow_html=True
    )

    c1, c2, c3, c4, c5 = st.columns(5)

    # Sonuç yüzdeleri
    home = 0
    draw = 0
    away = 0
    over = 0
    under = 0

    for score in analysis_df[
        "SKOR"
    ] if not analysis_df.empty else []:

        parsed = parse_score(
            score
        )

        if not parsed:
            continue

        h, a = parsed

        if h > a:
            home += 1
        elif h == a:
            draw += 1
        else:
            away += 1

        if h + a >= 3:
            over += 1
        else:
            under += 1

    count = max(
        1,
        len(
            analysis_df
        )
    )

    c1.metric(
        "Ev (1)",
        f"{home / count * 100:.1f}%"
    )

    c2.metric(
        "X",
        f"{draw / count * 100:.1f}%"
    )

    c3.metric(
        "Dep (2)",
        f"{away / count * 100:.1f}%"
    )

    c4.metric(
        "ÜST 2.5",
        f"{over / count * 100:.1f}%"
    )

    c5.metric(
        "ALT 2.5",
        f"{under / count * 100:.1f}%"
    )

    st.subheader(
        "⚽ GOL MARKETLERİ"
    )

    g1, g2, g3, g4 = st.columns(4)

    g1.metric(
        "EV 0.5 ÜST",
        f"{market['home05']:.1f}%"
    )

    g2.metric(
        "DEP 0.5 ÜST",
        f"{market['away05']:.1f}%"
    )

    g3.metric(
        "KG VAR",
        f"{market['btts']:.1f}%"
    )

    g4.metric(
        "ÜST 2.5",
        f"{market['over25']:.1f}%"
    )

    st.subheader(
        "🎯 EN ÇOK TEKRAR EDEN SKORLAR"
    )

    if analysis_df.empty:

        st.warning(
            "Benzer maç bulunamadı."
        )

    else:

        score_counter = Counter()

        for score in analysis_df[
            "SKOR"
        ]:

            if valid_score := parse_score(score):

                score_counter[
                    score
                ] += 1

        scores = score_counter.most_common(
            5
        )

        score_cols = st.columns(
            len(scores)
            if scores
            else 1
        )

        for i, (
            score,
            count_score
        ) in enumerate(scores):

            with score_cols[i]:

                st.markdown(
                    f"""
                    <div class='score-box'>
                        <div class='blue'>
                            {score}
                        </div>
                        <div class='small-text'>
                            {count_score} Kez
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    with st.expander(
        "🟢 BENZER MAÇLARI GÖSTER"
    ):

        if analysis_df.empty:

            st.write(
                "Benzer maç yok."
            )

        else:

            st.dataframe(
                analysis_df,
                use_container_width=True
            )


# =====================================================
# SAYFA 2
# YENİ MAÇLAR
# =====================================================

elif page == "Yeni Maçlar Seç":

    st.title(
        "✨ YENİ ÇEKİLEN MAÇLARIN ANALİZİ"
    )

    if today_df.empty:

        st.warning(
            "bugun_oranlar.xlsx boş veya bulunamadı."
        )

        st.stop()

    selected_new = st.selectbox(
        "Yeni Bülten Maçlarından Birini Seçin",
        ["MAÇ SEÇİNİZ"]
        +
        today_df["MAC"]
        .dropna()
        .tolist()
    )

    if selected_new == "MAÇ SEÇİNİZ":

        st.info(
            "Yeni bültenden bir maç seçin."
        )

        st.stop()

    row = today_df[
        today_df["MAC"]
        ==
        selected_new
    ].iloc[0]

    similar_df, tolerance = find_similar_matches(
        row["MS1"],
        row["MSX"],
        row["MS2"],
        row["UST_2_5"],
        row["ALT_2_5"],
        min_matches=4
    )

    market = calculate_goal_market_from_similar(
        similar_df
    )

    st.subheader(
        f"🔮 {selected_new}"
    )

    st.write(
        f"**Benzer geçmiş maç:** {len(similar_df)}"
        f" | **Tolerans:** {tolerance}"
    )

    c1, c2, c3, c4, c5 = st.columns(5)

    home = 0
    draw = 0
    away = 0
    over = 0
    under = 0

    for score in (
        similar_df["SKOR"]
        if not similar_df.empty
        else []
    ):

        parsed = parse_score(
            score
        )

        if not parsed:
            continue

        h, a = parsed

        if h > a:
            home += 1
        elif h == a:
            draw += 1
        else:
            away += 1

        if h + a >= 3:
            over += 1
        else:
            under += 1

    count = max(
        1,
        len(similar_df)
    )

    c1.metric(
        "MS1",
        f"{home / count * 100:.1f}%"
    )

    c2.metric(
        "MSX",
        f"{draw / count * 100:.1f}%"
    )

    c3.metric(
        "MS2",
        f"{away / count * 100:.1f}%"
    )

    c4.metric(
        "ÜST 2.5",
        f"{over / count * 100:.1f}%"
    )

    c5.metric(
        "ALT 2.5",
        f"{under / count * 100:.1f}%"
    )

    st.subheader(
        "⚽ GOL TERCİHLERİ"
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "EV 0.5 ÜST",
        f"{market['home05']:.1f}%"
    )

    c2.metric(
        "DEP 0.5 ÜST",
        f"{market['away05']:.1f}%"
    )

    c3.metric(
        "KG VAR",
        f"{market['btts']:.1f}%"
    )

    c4.metric(
        "ÜST 2.5",
        f"{market['over25']:.1f}%"
    )

    st.subheader(
        "🎯 TAHMİNİ SKORLAR"
    )

    if not similar_df.empty:

        counter = Counter(
            similar_df["SKOR"]
            .astype(str)
        )

        st.dataframe(
            pd.DataFrame(
                counter.most_common(10),
                columns=[
                    "SKOR",
                    "ADET"
                ]
            ),
            use_container_width=True,
            hide_index=True
        )

    with st.expander(
        "🟢 BENZER GEÇMİŞ MAÇLAR"
    ):

        if similar_df.empty:

            st.write(
                "Benzer maç yok."
            )

        else:

            st.dataframe(
                similar_df,
                use_container_width=True
            )


# =====================================================
# SAYFA 3
# BUGÜNÜN ENLERİ
# =====================================================

elif page == "🔥 BUGÜNÜN ENLERİ":

    st.title(
        "🔥 BUGÜNÜN EN YÜKSEK YÜZDELİ MAÇLARI"
    )

    st.caption(
        "Minimum 5 benzer geçmiş maç kriteri uygulanır."
    )

    if today_df.empty:

        st.warning(
            "Bugünkü maçlar bulunamadı."
        )

        st.stop()

    top_results = []

    progress = st.progress(
        0
    )

    total_today = len(
        today_df
    )

    for index, (_, row) in enumerate(
        today_df.iterrows()
    ):

        try:

            if any(
                pd.isna(
                    row[col]
                )
                for col in ODDS_COLUMNS
            ):
                progress.progress(
                    (index + 1)
                    /
                    total_today
                )
                continue

            similar_df, tolerance = find_similar_matches(
                row["MS1"],
                row["MSX"],
                row["MS2"],
                row["UST_2_5"],
                row["ALT_2_5"],
                min_matches=5
            )

            if len(similar_df) < 5:

                progress.progress(
                    (index + 1)
                    /
                    total_today
                )

                continue

            market = calculate_goal_market_from_similar(
                similar_df
            )

            home = 0
            draw = 0
            away = 0

            for score in similar_df[
                "SKOR"
            ]:

                parsed = parse_score(
                    score
                )

                if not parsed:
                    continue

                h, a = parsed

                if h > a:
                    home += 1

                elif h == a:
                    draw += 1

                else:
                    away += 1

            valid = max(
                1,
                len(similar_df)
            )

            top_score_counter = Counter(
                similar_df[
                    "SKOR"
                ].astype(str)
            )

            top_score = (
                top_score_counter
                .most_common(1)[0]
                if top_score_counter
                else (
                    "-",
                    0
                )
            )

            top_results.append(
                {
                    "MAC":
                        row["MAC"],

                    "MS1":
                        round(
                            home
                            /
                            valid
                            *
                            100,
                            1
                        ),

                    "MSX":
                        round(
                            draw
                            /
                            valid
                            *
                            100,
                            1
                        ),

                    "MS2":
                        round(
                            away
                            /
                            valid
                            *
                            100,
                            1
                        ),

                    "OVER":
                        market["over25"],

                    "UNDER":
                        100
                        -
                        market["over25"],

                    "EV_05":
                        market["home05"],

                    "DEP_05":
                        market["away05"],

                    "KG":
                        market["btts"],

                    "SAMPLE":
                        len(
                            similar_df
                        ),

                    "TOP_SCORE":
                        top_score[0],

                    "TOP_SCORE_COUNT":
                        top_score[1],

                    "TOLERANCE":
                        tolerance
                }
            )

        except Exception:
            pass

        progress.progress(
            (index + 1)
            /
            total_today
        )

    progress.empty()

    if not top_results:

        st.warning(
            "En az 5 benzer geçmiş maçı olan bugünkü maç bulunamadı."
        )

        st.stop()

    top_df = pd.DataFrame(
        top_results
    )

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(
        [
            "🏠 MS1",
            "🤝 MSX",
            "🚀 MS2",
            "⚽ ÜST 2.5",
            "🛡️ ALT 2.5",
            "🤝 KG VAR",
            "🏠 EV 0.5 ÜST",
            "✈️ DEP 0.5 ÜST"
        ]
    )

    def render_top_list(
        dataframe,
        column,
        title
    ):

        st.subheader(
            title
        )

        sorted_df = dataframe.sort_values(
            [
                column,
                "SAMPLE"
            ],
            ascending=[
                False,
                False
            ]
        ).head(10)

        for index, item in enumerate(
            sorted_df.to_dict(
                orient="records"
            ),
            1
        ):

            st.markdown(
                f"""
                <div class='top-card'>

                <b>
                #{index} - {item['MAC']}
                </b>

                <br><br>

                <span class='green'>
                %{item[column]:.1f}
                </span>

                <br>

                <span class='small-text'>
                Benzer Maç:
                {item['SAMPLE']}
                |
                MS1:
                %{item['MS1']:.1f}
                |
                X:
                %{item['MSX']:.1f}
                |
                MS2:
                %{item['MS2']:.1f}
                |
                EV 0.5:
                %{item['EV_05']:.1f}
                |
                DEP 0.5:
                %{item['DEP_05']:.1f}
                |
                KG:
                %{item['KG']:.1f}
                |
                Skor:
                {item['TOP_SCORE']}
                </span>

                </div>
                """,
                unsafe_allow_html=True
            )

    with tab1:
        render_top_list(
            top_df,
            "MS1",
            "🏠 EN YÜKSEK MS1"
        )

    with tab2:
        render_top_list(
            top_df,
            "MSX",
            "🤝 EN YÜKSEK BERABERLİK"
        )

    with tab3:
        render_top_list(
            top_df,
            "MS2",
            "🚀 EN YÜKSEK MS2"
        )

    with tab4:
        render_top_list(
            top_df,
            "OVER",
            "⚽ EN YÜKSEK 2.5 ÜST"
        )

    with tab5:
        render_top_list(
            top_df,
            "UNDER",
            "🛡️ EN YÜKSEK 2.5 ALT"
        )

    with tab6:
        render_top_list(
            top_df,
            "KG",
            "🤝 EN YÜKSEK KG VAR"
        )

    with tab7:
        render_top_list(
            top_df,
            "EV_05",
            "🏠 EN YÜKSEK EV 0.5 ÜST"
        )

    with tab8:
        render_top_list(
            top_df,
            "DEP_05",
            "✈️ EN YÜKSEK DEP 0.5 ÜST"
        )

    with st.expander(
        "📋 TÜM SONUÇLARI GÖSTER"
    ):

        st.dataframe(
            top_df,
            use_container_width=True,
            hide_index=True
        )


# =====================================================
# SAYFA 4
# TAKIM DETAY
# =====================================================

elif page == "👥 TAKIM DETAY":

    st.title(
        "👥 TAKIM DETAY ANALİZİ"
    )

    st.caption(
        "Bir takımın en az 3 geçmiş maçı bulunmadan takım analizi yapılmaz."
    )

    if not valid_teams:

        st.warning(
            "En az 3 geçmiş maçı bulunan takım yok."
        )

        st.stop()

    selected_team = st.selectbox(
        "Takım seçin",
        valid_teams
    )

    team_history = team_matches[
        selected_team
    ]

    team_stats = calculate_team_stats(
        team_matches,
        selected_team
    )

    if team_stats is None:

        st.error(
            "Bu takımın yeterli geçmiş maçı yok."
        )

        st.stop()

    # =================================================
    # TAKIM GENEL BİLGİ
    # =================================================

    st.subheader(
        f"📊 {selected_team}"
    )

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        "Maç",
        team_stats["matches"]
    )

    c2.metric(
        "Puan",
        team_stats["points"]
    )

    c3.metric(
        "Puan / Maç",
        team_stats["ppm"]
    )

    c4.metric(
        "Galibiyet",
        f"{team_stats['win_pct']:.1f}%"
    )

    c5.metric(
        "Form Durumu",
        (
            "GÜÇLÜ"
            if team_stats["win_pct"] >= 60
            else
            "ORTA"
            if team_stats["win_pct"] >= 40
            else
            "ZAYIF"
        )
    )

    # =================================================
    # GOL İSTATİSTİKLERİ
    # =================================================

    st.subheader(
        "⚽ TAKIM GOL PROFİLİ"
    )

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        "Attığı Gol Ort.",
        team_stats["gf_avg"]
    )

    c2.metric(
        "Yediği Gol Ort.",
        team_stats["ga_avg"]
    )

    c3.metric(
        "Takım Gol Attı",
        f"{team_stats['team_score_pct']:.1f}%"
    )

    c4.metric(
        "KG VAR",
        f"{team_stats['btts_pct']:.1f}%"
    )

    c5.metric(
        "ÜST 2.5",
        f"{team_stats['over25_pct']:.1f}%"
    )

    # =================================================
    # BUGÜNKÜ MAÇLAR
    # SEÇİLEN TAKIMIN OLDUĞU MAÇLAR
    # =================================================

    st.subheader(
        "🔥 BUGÜN BU TAKIMIN MAÇLARI"
    )

    today_team_matches = today_df[
        (
            today_df["HOME_TEAM"]
            ==
            selected_team
        )
        |
        (
            today_df["AWAY_TEAM"]
            ==
            selected_team
        )
    ].copy()

    if today_team_matches.empty:

        st.info(
            "Bugünkü bültende bu takımın maçı bulunamadı."
        )

    else:

        team_today_results = []

        for _, row in today_team_matches.iterrows():

            similar_df, tolerance = find_similar_matches(
                row["MS1"],
                row["MSX"],
                row["MS2"],
                row["UST_2_5"],
                row["ALT_2_5"],
                min_matches=3
            )

            market = calculate_goal_market_from_similar(
                similar_df
            )

            # -------------------------------------------------
            # Seçilen takım EV mi DEP mi?
            # -------------------------------------------------

            if (
                row["HOME_TEAM"]
                ==
                selected_team
            ):

                team_market_probability = (
                    market["home05"]
                )

                selected_market = (
                    "EV 0.5 ÜST"
                )

            else:

                team_market_probability = (
                    market["away05"]
                )

                selected_market = (
                    "DEP 0.5 ÜST"
                )

            team_today_results.append(
                {
                    "MAÇ":
                        row["MAC"],

                    "RAKİP":
                        (
                            row["AWAY_TEAM"]
                            if row["HOME_TEAM"]
                            ==
                            selected_team
                            else
                            row["HOME_TEAM"]
                        ),

                    "SAHA":
                        (
                            "EV"
                            if row["HOME_TEAM"]
                            ==
                            selected_team
                            else
                            "DEP"
                        ),

                    "SEÇİLEN MARKET":
                        selected_market,

                    "TAKIM 0.5 ÜST":
                        team_market_probability,

                    "EV 0.5 ÜST":
                        market["home05"],

                    "DEP 0.5 ÜST":
                        market["away05"],

                    "KG VAR":
                        market["btts"],

                    "ÜST 2.5":
                        market["over25"],

                    "BENZER MAÇ":
                        market["sample"],

                    "TOLERANS":
                        tolerance
                }
            )

        today_team_df = pd.DataFrame(
            team_today_results
        )

        if not today_team_df.empty:

            today_team_df.sort_values(
                "TAKIM 0.5 ÜST",
                ascending=False,
                inplace=True
            )

            st.dataframe(
                today_team_df,
                use_container_width=True,
                hide_index=True
            )

            st.markdown(
                "### 🏆 Bugün Bu Takım İçin En Güçlü 0.5 ÜST"
            )

            best_today = today_team_df.iloc[
                0
            ]

            st.metric(
                f"{selected_team} - {best_today['SEÇİLEN MARKET']}",
                f"{best_today['TAKIM 0.5 ÜST']:.1f}%"
            )

            st.caption(
                f"Maç: {best_today['MAÇ']} | "
                f"Benzer geçmiş maç: "
                f"{best_today['BENZER MAÇ']}"
            )

    # =================================================
    # TAKIMIN GEÇMİŞİ
    # =================================================

    st.subheader(
        "📚 TAKIMIN GEÇMİŞ MAÇLARI"
    )

    team_history_df = pd.DataFrame(
        team_history
    )

    if not team_history_df.empty:

        st.dataframe(
            team_history_df[
                [
                    "MAC",
                    "OPPONENT",
                    "VENUE",
                    "TEAM_GOALS",
                    "OPP_GOALS",
                    "TOTAL_GOALS",
                    "WIN",
                    "DRAW",
                    "LOSS",
                    "TEAM_SCORED",
                    "BTTS"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

    # =================================================
    # TAKIMIN ORAN PROFİLİNE BENZER GEÇMİŞ MAÇLAR
    # =================================================

    st.subheader(
        "🔍 TAKIMIN ORAN PROFİLİNE BENZER GEÇMİŞ MAÇLAR"
    )

    st.caption(
        "Burada seçilen takımın bugünkü oran profiline en çok benzeyen geçmiş maçları kullanılır."
    )

    if today_team_matches.empty:

        st.info(
            "Bugünkü takım maçı bulunamadı."
        )

    else:

        for match_index, (_, today_row) in enumerate(
            today_team_matches.iterrows(),
            1
        ):

            st.markdown(
                f"#### #{match_index} {today_row['MAC']}"
            )

            similar_team_df, tolerance = get_team_similar_history(
                selected_team,
                today_row["MS1"],
                today_row["MSX"],
                today_row["MS2"],
                today_row["UST_2_5"],
                today_row["ALT_2_5"],
                min_matches=3
            )

            if similar_team_df.empty:

                st.warning(
                    "Bu takımın oran profiline yeterli benzer geçmiş maç bulunamadı."
                )

                continue

            team_market = calculate_goal_market_from_similar(
                similar_team_df
            )

            c1, c2, c3, c4, c5 = st.columns(5)

            c1.metric(
                "Takım Maç Örneklemi",
                len(
                    similar_team_df
                )
            )

            c2.metric(
                "EV 0.5 ÜST",
                f"{team_market['home05']:.1f}%"
            )

            c3.metric(
                "DEP 0.5 ÜST",
                f"{team_market['away05']:.1f}%"
            )

            c4.metric(
                "KG VAR",
                f"{team_market['btts']:.1f}%"
            )

            c5.metric(
                "ÜST 2.5",
                f"{team_market['over25']:.1f}%"
            )

            st.caption(
                f"Kullanılan tolerans: {tolerance}"
            )

            with st.expander(
                "Benzer geçmiş maçları göster"
            ):

                st.dataframe(
                    similar_team_df[
                        [
                            "MAC",
                            "SKOR",
                            "MS1",
                            "MSX",
                            "MS2",
                            "UST_2_5",
                            "ALT_2_5",
                            "SIM"
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True
                )

    # =================================================
    # BUGÜNÜN TÜM MAÇLARINDAN
    # SEÇİLEN TAKIMIN EV/DEP 0.5 ÜST ANALİZİ
    # =================================================

    st.subheader(
        "🎯 BUGÜNÜN MAÇLARI ARASINDA TAKIM 0.5 ÜST SIRALAMASI"
    )

    if today_team_matches.empty:

        st.info(
            "Bugün bu takımın maçı yok."
        )

    else:

        ranking_rows = []

        for _, row in today_team_matches.iterrows():

            similar_df, tolerance = get_team_similar_history(
                selected_team,
                row["MS1"],
                row["MSX"],
                row["MS2"],
                row["UST_2_5"],
                row["ALT_2_5"],
                min_matches=3
            )

            if (
                similar_df.empty
                or
                len(similar_df) < 3
            ):
                continue

            market = calculate_goal_market_from_similar(
                similar_df
            )

            if (
                row["HOME_TEAM"]
                ==
                selected_team
            ):

                probability = market[
                    "home05"
                ]

                market_name = (
                    "EV 0.5 ÜST"
                )

            else:

                probability = market[
                    "away05"
                ]

                market_name = (
                    "DEP 0.5 ÜST"
                )

            ranking_rows.append(
                {
                    "MAÇ":
                        row["MAC"],

                    "MARKET":
                        market_name,

                    "OLASILIK":
                        probability,

                    "ÖRNEKLEM":
                        market["sample"],

                    "KG":
                        market["btts"],

                    "ÜST 2.5":
                        market["over25"],

                    "TOLERANS":
                        tolerance
                }
            )

        ranking_df = pd.DataFrame(
            ranking_rows
        )

        if ranking_df.empty:

            st.warning(
                "En az 3 benzer geçmiş maçı sağlayan bugünkü karşılaşma bulunamadı."
            )

        else:

            ranking_df.sort_values(
                [
                    "OLASILIK",
                    "ÖRNEKLEM"
                ],
                ascending=[
                    False,
                    False
                ],
                inplace=True
            )

            st.dataframe(
                ranking_df,
                use_container_width=True,
                hide_index=True
            )


# =====================================================
# FOOTER
# =====================================================

st.markdown("---")

st.caption(
    "ORAN ANALİZ PANELİ • Oran benzerliği ve geçmiş skor analizi"
)