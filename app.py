import os
from io import BytesIO, StringIO
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import requests
import joblib

import streamlit as st
from math import exp, factorial

from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.formatting.rule import CellIsRule



import os
from io import BytesIO, StringIO
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import requests
import joblib
import streamlit as st
from math import exp, factorial
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.formatting.rule import CellIsRule

# NEMA VIŠE gdown-a ❌
# import gdown  -> maknuti ako još stoji
import pickle  # može ostati, ali ti realno više ni ne treba

# Google Drive IDs – tvoji linkovi
GDRIVE_ID_AI_1X2 = "1mgbkAo6p7vo9syYQpkV3uOgX_UsCwJ0i"
GDRIVE_ID_AI_GOALS = "1KifFjTHCqD7_E64O0SZXxfkfMMiPGgpL"

def download_from_gdrive(file_id: str, output_path: str):
    """
    Jednostavan download s Google Drive-a preko requests.
    Radi i na Streamlit Cloud-u.
    """
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERR] Google Drive download failed for {file_id}: {e}")
        return False

    try:
        with open(output_path, "wb") as f:
            f.write(resp.content)
        print(f"[OK] Downloaded {output_path} from Google Drive.")
        return True
    except Exception as e:
        print(f"[ERR] Saving file failed {output_path}: {e}")
        return False


def ensure_model_files():
    """
    Provjerava da postoje model fajlovi u /models.
    Ako ne postoje – skida ih s Google Drive-a.
    """
    os.makedirs("models", exist_ok=True)

    model_1x2_path = os.path.join("models", "ai_1x2_model.pkl")
    goals_model_path = os.path.join("models", "ai_goals_models.pkl")

    if not os.path.exists(model_1x2_path):
        print("[INFO] ai_1x2_model.pkl not found – downloading from Google Drive...")
        ok = download_from_gdrive(GDRIVE_ID_AI_1X2, model_1x2_path)
        if not ok:
            print("[WARN] Could not download ai_1x2_model.pkl")

    if not os.path.exists(goals_model_path):
        print("[INFO] ai_goals_models.pkl not found – downloading from Google Drive...")
        ok = download_from_gdrive(GDRIVE_ID_AI_GOALS, goals_model_path)
        if not ok:
            print("[WARN] Could not download ai_goals_models.pkl")


# ----------------------
# SIMPLE PASSWORD LOGIN
# ----------------------
def check_password():
    # Ensure session state key exists
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    # If already authenticated → continue
    if st.session_state["authenticated"]:
        return True

    st.title("🔐 Login required")

    password = st.text_input("Enter password:", type="password")

    if st.button("Login"):
        if password == "Vice142536":   # 🔑 LOZINKA OVDJE
            st.session_state["authenticated"] = True
            st.success("Login successful!")

            # Force soft refresh using st.query_params
            st.query_params["auth"] = "1"
            st.stop()
        else:
            st.error("Wrong password")

    st.stop()



# -------------------------------
# PRO CSS – look & feel
# -------------------------------

def inject_pro_css():
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 2rem;
            max-width: 1200px;
        }
        .hero {
            padding: 1.2rem 1.5rem;
            border-radius: 16px;
            background: linear-gradient(90deg, #0f172a, #1e293b);
            color: #e5e7eb;
            margin-bottom: 1.2rem;
            border: 1px solid #1f2937;
        }
        .hero-title {
            font-size: 1.6rem;
            font-weight: 700;
            margin-bottom: 0.2rem;
        }
        .hero-subtitle {
            font-size: 0.9rem;
            color: #9ca3af;
        }
        .kpi-card {
            border-radius: 14px;
            padding: 0.8rem 0.9rem;
            background: #0b1120;
            border: 1px solid #1f2937;
            color: #e5e7eb;
            margin-bottom: 0.8rem;
        }
        .kpi-label {
            font-size: 0.8rem;
            color: #9ca3af;
            margin-bottom: 0.2rem;
        }
        .kpi-main {
            font-size: 1.2rem;
            font-weight: 600;
        }
        .kpi-sub {
            font-size: 0.75rem;
            color: #6b7280;
        }
        button[data-baseweb="tab"] {
            font-size: 0.9rem;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# -------------------------------
# CONFIG
# -------------------------------

DEFAULT_SEASON = "2526"
HISTORICAL_SEASONS = ["2526", "2425", "2324", "2223", "2122"]

ALL_LEAGUES: Dict[str, str] = {
    "Premier League": "E0",
    "Championship": "E1",
    "League One": "E2",
    "League Two": "E3",
    "National League": "EC",
    "Bundesliga": "D1",
    "2. Bundesliga": "D2",
    "Serie A": "I1",
    "Serie B": "I2",
    "La Liga": "SP1",
    "La Liga 2": "SP2",
    "Ligue 1": "F1",
    "Ligue 2": "F2",
    "Eredivisie": "N1",
    "Jupiler Pro League": "B1",
    "Primeira Liga": "P1",
    "Scotland Premier": "SC0",
    "Scotland Championship": "SC1",
    "Scotland League One": "SC2",
    "Scotland League Two": "SC3",
    "Super Lig": "T1",
    "Super League Greece": "G1",
}

BASE_URL = "https://www.football-data.co.uk/mmz4281/{season}/{league_code}.csv"
FIXTURES_URL = "https://www.football-data.co.uk/fixtures.csv"

RAW_FOOTBALL_DIR = os.path.join("data", "raw", "football_data")
os.makedirs(RAW_FOOTBALL_DIR, exist_ok=True)
os.makedirs("models", exist_ok=True)

# Dixon–Coles rho
DC_RHO = 0.13


# -------------------------------
# DOWNLOAD & LOAD HELPERS
# -------------------------------

def download_csv(url: str, dest_path: str) -> None:
    if os.path.exists(dest_path):
        return
    try:
        resp = requests.get(url, timeout=30)
    except Exception as e:
        print(f"[ERR] request failed {url}: {e}")
        return
    if resp.status_code != 200:
        print(f"[ERR] {url} -> {resp.status_code}")
        return
    with open(dest_path, "wb") as f:
        f.write(resp.content)
    print(f"[OK] {url} -> {dest_path}")


def load_all_leagues(season_code: str) -> pd.DataFrame:
    all_dfs = []
    for league_name, league_code in ALL_LEAGUES.items():
        url = BASE_URL.format(season=season_code, league_code=league_code)
        filename = f"{season_code}_{league_code}.csv"
        dest_path = os.path.join(RAW_FOOTBALL_DIR, filename)

        download_csv(url, dest_path)

        if os.path.exists(dest_path):
            try:
                df = pd.read_csv(dest_path, encoding="latin1")
                df["league"] = league_name
                df["league_code"] = league_code
                df["season_code"] = season_code
                all_dfs.append(df)
            except Exception as e:
                print(f"[ERR] loading {dest_path}: {e}")

    if not all_dfs:
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)
    if "Date" in combined.columns:
        combined["Date"] = pd.to_datetime(combined["Date"], dayfirst=True, errors="coerce")
    else:
        combined["Date"] = pd.NaT

    return combined


def load_all_leagues_multi(seasons: List[str]) -> pd.DataFrame:
    all_dfs = []
    for s in seasons:
        df = load_all_leagues(s)
        if not df.empty:
            all_dfs.append(df)
    if not all_dfs:
        return pd.DataFrame()
    return pd.concat(all_dfs, ignore_index=True)


def load_fixtures_from_web() -> pd.DataFrame:
    """
    Load fixtures.csv from football-data.co.uk, fix BOM and decimal commas.
    """
    try:
        resp = requests.get(FIXTURES_URL, timeout=30)
        if resp.status_code != 200:
            print(f"[WARN] fixtures.csv status {resp.status_code}")
            return pd.DataFrame()

        text = resp.content.decode("latin1", errors="ignore")
        df = pd.read_csv(StringIO(text), sep=None, engine="python")
    except Exception as e:
        print(f"[WARN] load_fixtures_from_web error: {e}")
        return pd.DataFrame()

    # clean BOM, spaces, etc.
    cleaned_cols = []
    for c in df.columns:
        c = str(c)
        c = c.replace("\ufeff", "")  # real BOM
        c = c.replace("ï»¿", "")    # mis-decoded BOM
        c = c.strip()
        cleaned_cols.append(c)
    df.columns = cleaned_cols

    required = ["Div", "Date", "HomeTeam", "AwayTeam"]
    if not all(col in df.columns for col in required):
        print("[WARN] fixtures.csv does not have expected columns:", df.columns.tolist())
        return pd.DataFrame()

    code_to_name = {v: k for k, v in ALL_LEAGUES.items()}
    df["league_code"] = df["Div"].astype(str).str.strip()
    df["league"] = df["league_code"].map(code_to_name)
    df = df[df["league"].notna()].copy()

    df["season_code"] = DEFAULT_SEASON
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")

    if "FTHG" not in df.columns:
        df["FTHG"] = np.nan
    if "FTAG" not in df.columns:
        df["FTAG"] = np.nan

    # decimal commas -> dot for main odds
    for col in ["B365H", "B365D", "B365A", "B365>2.5", "B365<2.5"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", ".", regex=False)
                .replace("", np.nan)
                .astype(float)
            )

    # BTTS odds (if present)
    for col in ["BTSH", "BTSD"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", ".", regex=False)
                .replace("", np.nan)
                .astype(float)
            )

    return df


# -------------------------------
# POISSON + DIXON-COLES
# -------------------------------

def poisson_pmf(k: int, lam: float) -> float:
    return (lam ** k) * exp(-lam) / factorial(k)


def dixon_coles_tau(hg: int, ag: int, lam_home: float, lam_away: float, rho: float) -> float:
    if hg == 0 and ag == 0:
        return 1 - (lam_home + lam_away) * rho
    elif hg == 0 and ag == 1:
        return 1 + lam_home * rho
    elif hg == 1 and ag == 0:
        return 1 + lam_away * rho
    elif hg == 1 and ag == 1:
        return 1 - rho
    else:
        return 1.0


def match_probabilities_dc(
    lam_home: float,
    lam_away: float,
    rho: float = DC_RHO,
    max_goals: int = 10,
) -> Dict[str, float]:
    p_home = p_draw = p_away = 0.0
    total = 0.0

    for hg in range(0, max_goals + 1):
        p_hg = poisson_pmf(hg, lam_home)
        for ag in range(0, max_goals + 1):
            p_ag = poisson_pmf(ag, lam_away)
            base = p_hg * p_ag
            tau = dixon_coles_tau(hg, ag, lam_home, lam_away, rho)
            val = base * tau
            total += val

            if hg > ag:
                p_home += val
            elif hg == ag:
                p_draw += val
            else:
                p_away += val

    if total > 0:
        p_home /= total
        p_draw /= total
        p_away /= total

    return {"p_home": p_home, "p_draw": p_draw, "p_away": p_away}


def goal_market_probs(lam_home: float, lam_away: float, rho: float = DC_RHO, max_goals: int = 10):
    """
    Poisson/DC probabilities for:
    - over 2.5 goals
    - BTTS (yes)
    """
    p_over25 = 0.0
    p_btts = 0.0
    total = 0.0

    for hg in range(0, max_goals + 1):
        p_hg = poisson_pmf(hg, lam_home)
        for ag in range(0, max_goals + 1):
            p_ag = poisson_pmf(ag, lam_away)
            base = p_hg * p_ag
            tau = dixon_coles_tau(hg, ag, lam_home, lam_away, rho)
            p = base * tau
            total += p

            if hg + ag >= 3:
                p_over25 += p
            if hg > 0 and ag > 0:
                p_btts += p

    if total > 0:
        p_over25 /= total
        p_btts /= total

    return p_over25, p_btts


# -------------------------------
# TEAM STRENGTHS
# -------------------------------

def compute_team_strengths(df: pd.DataFrame) -> pd.DataFrame:
    league_stats = df.groupby("league").agg(
        avg_home_goals=("FTHG", "mean"),
        avg_away_goals=("FTAG", "mean"),
    ).reset_index()

    home_stats = df.groupby(["league", "HomeTeam"]).agg(
        home_goals_for=("FTHG", "sum"),
        home_goals_against=("FTAG", "sum"),
        home_games=("HomeTeam", "count"),
    ).reset_index().rename(columns={"HomeTeam": "team"})

    away_stats = df.groupby(["league", "AwayTeam"]).agg(
        away_goals_for=("FTAG", "sum"),
        away_goals_against=("FTHG", "sum"),
        away_games=("AwayTeam", "count"),
    ).reset_index().rename(columns={"AwayTeam": "team"})

    teams = pd.merge(home_stats, away_stats, on=["league", "team"], how="outer")
    teams = teams.merge(league_stats, on="league", how="left")

    for col in [
        "home_goals_for",
        "home_goals_against",
        "home_games",
        "away_goals_for",
        "away_goals_against",
        "away_games",
    ]:
        teams[col] = teams[col].fillna(0)

    teams["home_games"] = teams["home_games"].replace(0, np.nan)
    teams["away_games"] = teams["away_games"].replace(0, np.nan)

    teams["home_goals_for_avg"] = teams["home_goals_for"] / teams["home_games"]
    teams["home_goals_against_avg"] = teams["home_goals_against"] / teams["home_games"]
    teams["away_goals_for_avg"] = teams["away_goals_for"] / teams["away_games"]
    teams["away_goals_against_avg"] = teams["away_goals_against"] / teams["away_games"]

    teams["home_goals_for_avg"] = teams["home_goals_for_avg"].fillna(teams["avg_home_goals"])
    teams["home_goals_against_avg"] = teams["home_goals_against_avg"].fillna(teams["avg_away_goals"])
    teams["away_goals_for_avg"] = teams["away_goals_for_avg"].fillna(teams["avg_away_goals"])
    teams["away_goals_against_avg"] = teams["away_goals_against_avg"].fillna(teams["avg_home_goals"])

    teams["att_home"] = teams["home_goals_for_avg"] / teams["avg_home_goals"]
    teams["def_home"] = teams["home_goals_against_avg"] / teams["avg_away_goals"]
    teams["att_away"] = teams["away_goals_for_avg"] / teams["avg_away_goals"]
    teams["def_away"] = teams["away_goals_against_avg"] / teams["avg_home_goals"]

    for col in ["att_home", "def_home", "att_away", "def_away"]:
        teams[col] = teams[col].replace([np.inf, -np.inf], np.nan).fillna(1.0)

    return teams


def expected_goals_for_match(
    league_avg_home: float,
    league_avg_away: float,
    home_team_row: pd.Series,
    away_team_row: pd.Series,
) -> Tuple[float, float]:
    lam_home = league_avg_home * home_team_row["att_home"] * away_team_row["def_away"]
    lam_away = league_avg_away * away_team_row["att_away"] * home_team_row["def_home"]
    return max(lam_home, 0.01), max(lam_away, 0.01)


# -------------------------------
# FAIR ODDS + EDGE + KELLY
# -------------------------------

def fair_odds(p: float) -> float:
    if p is None or np.isnan(p) or p <= 0:
        return np.nan
    return 1.0 / p


def compute_edge_and_kelly(p: float, odds: float) -> Tuple[float, float]:
    if p is None or np.isnan(p) or odds is None or np.isnan(odds) or odds <= 1:
        return np.nan, 0.0
    edge = p * odds - 1.0
    if edge <= 0:
        return edge, 0.0
    kelly = edge / (odds - 1.0)
    return edge, kelly


# -------------------------------
# AI FT 1X2 – APPLY
# -------------------------------

# -----------------------------------------
# FT 1X2 – AI MODEL (LOCAL + GOOGLE DRIVE)
# -----------------------------------------

def load_ai_1x2_model():
    """
    Pokušaj:
    1) uzeti model iz models/ai_1x2_model.pkl
    2) ako ne postoji – skini ga sa Google Drive-a
    3) ako ni to ne uspije – digni izuzetak
    """
    model_path = os.path.join("models", "ai_1x2_model.pkl")

    # 1) Ako već postoji lokalno – koristi to
    if not os.path.exists(model_path):
        try:
            # 2) ako ne postoji, skidamo s Google Drive-a
            download_from_gdrive(GDRIVE_ID_AI_1X2, model_path)
        except Exception as e:
            print("[ERR] Cannot download AI 1X2 model from GDrive:", e)
            raise

    artifact = joblib.load(model_path)
    return artifact["model"], artifact["feature_cols"]


def apply_ai_model(pred_df: pd.DataFrame) -> pd.DataFrame:
    if pred_df.empty:
        return pred_df

    # Pokušaj učitati model; ako ne uspije – samo vrati NaN stupce
    try:
        model, feature_cols = load_ai_1x2_model()
    except Exception as e:
        print("[WARN] AI 1X2 model not available, using NaN probabilities:", e)
        pred_df = pred_df.copy()
        pred_df["ai_p_home"] = np.nan
        pred_df["ai_p_draw"] = np.nan
        pred_df["ai_p_away"] = np.nan
        return pred_df

    df = pred_df.copy()

    # Osiguraj da odds kolone postoje
    if "B365H" not in df.columns and "book_home" in df.columns:
        df["B365H"] = df["book_home"]
    if "B365D" not in df.columns and "book_draw" in df.columns:
        df["B365D"] = df["book_draw"]
    if "B365A" not in df.columns and "book_away" in df.columns:
        df["B365A"] = df["book_away"]

    # Feature matrica
    X = df.reindex(columns=feature_cols, fill_value=0.0)

    # Predikcije
    prob_matrix = model.predict_proba(X)
    class_to_index = {cls: idx for idx, cls in enumerate(model.classes_)}

    df["ai_p_home"] = prob_matrix[:, class_to_index[0]]
    df["ai_p_draw"] = prob_matrix[:, class_to_index[1]]
    df["ai_p_away"] = prob_matrix[:, class_to_index[2]]

    return df



# -------------------------------
# AI GOALS MODELS – TRAIN & APPLY
# -------------------------------

def train_ai_goals_models(df_all: pd.DataFrame) -> None:
    df_played = df_all.dropna(subset=["FTHG", "FTAG"]).copy()
    if df_played.empty:
        print("[ERR] No played matches for goals AI training.")
        return

    teams = compute_team_strengths(df_played)
    league_stats = df_played.groupby("league").agg(
        avg_home_goals=("FTHG", "mean"),
        avg_away_goals=("FTAG", "mean"),
    ).reset_index()

    rows = []
    y_over25 = []
    y_btts = []
    y_total_goals = []

    for _, row in df_played.iterrows():
        league = row["league"]
        home = row["HomeTeam"]
        away = row["AwayTeam"]

        ls = league_stats[league_stats["league"] == league]
        if ls.empty:
            continue
        lg = ls.iloc[0]
        avg_h = lg["avg_home_goals"]
        avg_a = lg["avg_away_goals"]

        ht_rows = teams[(teams["league"] == league) & (teams["team"] == home)]
        at_rows = teams[(teams["league"] == league) & (teams["team"] == away)]
        if ht_rows.empty or at_rows.empty:
            continue

        ht = ht_rows.iloc[0]
        at = at_rows.iloc[0]

        lam_home, lam_away = expected_goals_for_match(avg_h, avg_a, ht, at)
        p_over25, p_btts = goal_market_probs(lam_home, lam_away, rho=DC_RHO, max_goals=10)

        fthg = row["FTHG"]
        ftag = row["FTAG"]
        total_goals = fthg + ftag

        label_over25 = 1 if total_goals >= 3 else 0
        label_btts = 1 if (fthg > 0 and ftag > 0) else 0

        feature_row = {
            "lambda_home": lam_home,
            "lambda_away": lam_away,
            "p_over25_poi": p_over25,
            "p_btts_poi": p_btts,
        }

        for col in ["B365H", "B365D", "B365A"]:
            if col in df_played.columns:
                feature_row[col] = row.get(col, np.nan)

        rows.append(feature_row)
        y_over25.append(label_over25)
        y_btts.append(label_btts)
        y_total_goals.append(total_goals)

    X = pd.DataFrame(rows).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    y_over25 = pd.Series(y_over25, name="over25")
    y_btts = pd.Series(y_btts, name="btts")
    y_total_goals = pd.Series(y_total_goals, name="total_goals")

    if X.empty:
        print("[ERR] Goals dataset empty – no training.")
        return

    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score

    # Over/Under 2.5
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_over25, test_size=0.25, random_state=42, stratify=y_over25
    )
    over_model = RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        random_state=42,
        n_jobs=-1,
    )
    print("[INFO] Training RF for Over/Under 2.5...")
    over_model.fit(X_train, y_train)
    y_pred = over_model.predict(X_test)
    acc_over = accuracy_score(y_test, y_pred)
    print(f"[RESULT] Over/Under 2.5 AI accuracy: {acc_over:.3f}")

    # BTTS
    X_train2, X_test2, y_train2, y_test2 = train_test_split(
        X, y_btts, test_size=0.25, random_state=42, stratify=y_btts
    )
    btts_model = RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        random_state=42,
        n_jobs=-1,
    )
    print("[INFO] Training RF for BTTS...")
    btts_model.fit(X_train2, y_train2)
    y_pred2 = btts_model.predict(X_test2)
    acc_btts = accuracy_score(y_test2, y_pred2)
    print(f"[RESULT] BTTS AI accuracy: {acc_btts:.3f}")

    # total goals
    X_train3, X_test3, y_train3, y_test3 = train_test_split(
        X, y_total_goals, test_size=0.25, random_state=42
    )
    goals_model = RandomForestRegressor(
        n_estimators=300,
        max_depth=12,
        random_state=42,
        n_jobs=-1,
    )
    print("[INFO] Training RF regressor for total goals...")
    goals_model.fit(X_train3, y_train3)
    y_pred3 = goals_model.predict(X_test3)
    mae = np.mean(np.abs(y_pred3 - y_test3))
    print(f"[RESULT] Total goals MAE: {mae:.3f}")

    artifact = {
        "feature_cols": list(X.columns),
        "over25_model": over_model,
        "btts_model": btts_model,
        "goals_model": goals_model,
    }
    joblib.dump(artifact, os.path.join("models", "ai_goals_models.pkl"))
    print("[OK] Goals AI models saved to models/ai_goals_models.pkl")


# -----------------------------------------
# GOALS – AI MODELI (OU 2.5, BTTS, TOTAL GOALS)
# -----------------------------------------

def ensure_ai_goals_models(df_all: pd.DataFrame) -> None:
    """
    Na Streamlitu:
    1) prvo pokušaj skinuti goals model s Google Drive-a
    2) ako ne uspije – fallback: treniraj lokalno (može biti sporo)
    """
    model_path = os.path.join("models", "ai_goals_models.pkl")
    if os.path.exists(model_path):
        return

    try:
        print("[INFO] Downloading AI goals models from Google Drive...")
        download_from_gdrive(GDRIVE_ID_AI_GOALS, model_path)
        return
    except Exception as e:
        print("[WARN] Cannot download AI goals models, training locally:", e)
        # Ako baš ništa – onda treniraj (lokalno OK, u cloudu može biti sporo)
        train_ai_goals_models(df_all)


def apply_ai_goals(pred_df: pd.DataFrame) -> pd.DataFrame:
    if pred_df.empty:
        return pred_df

    model_path = os.path.join("models", "ai_goals_models.pkl")
    if not os.path.exists(model_path):
        # Pokušaj osigurati model (download ili trening)
        ensure_ai_goals_models(pred_df.assign(FTHG=np.nan, FTAG=np.nan))

    if not os.path.exists(model_path):
        # I dalje nema – digni NaN i nastavi
        print("[WARN] AI goals model still not available, using NaN outputs.")
        pred_df = pred_df.copy()
        pred_df["ai_p_over25"] = np.nan
        pred_df["ai_p_under25"] = np.nan
        pred_df["ai_p_btts_yes"] = np.nan
        pred_df["ai_p_btts_no"] = np.nan
        pred_df["ai_total_goals"] = np.nan
        return pred_df

    try:
        artifact = joblib.load(model_path)
    except Exception as e:
        print("[ERR] Failed to load AI goals model:", e)
        pred_df = pred_df.copy()
        pred_df["ai_p_over25"] = np.nan
        pred_df["ai_p_under25"] = np.nan
        pred_df["ai_p_btts_yes"] = np.nan
        pred_df["ai_p_btts_no"] = np.nan
        pred_df["ai_total_goals"] = np.nan
        return pred_df

    feature_cols = artifact["feature_cols"]
    over_model = artifact["over25_model"]
    btts_model = artifact["btts_model"]
    goals_model = artifact["goals_model"]

    df = pred_df.copy()

    # Ako koristiš B365H/D/A u feature-ima, pobrini se da postoje
    if "B365H" not in df.columns and "book_home" in df.columns:
        df["B365H"] = df["book_home"]
    if "B365D" not in df.columns and "book_draw" in df.columns:
        df["B365D"] = df["book_draw"]
    if "B365A" not in df.columns and "book_away" in df.columns:
        df["B365A"] = df["book_away"]

    X = df.reindex(columns=feature_cols, fill_value=0.0)

    # OU 2.5
    prob_over = over_model.predict_proba(X)[:, 1]
    df["ai_p_over25"] = prob_over
    df["ai_p_under25"] = 1.0 - prob_over

    # BTTS
    prob_btts = btts_model.predict_proba(X)[:, 1]
    df["ai_p_btts_yes"] = prob_btts
    df["ai_p_btts_no"] = 1.0 - prob_btts

    # Total goals (regresija)
    df["ai_total_goals"] = goals_model.predict(X)

    return df



# -------------------------------
# GENERATE PREDICTIONS
# -------------------------------

def generate_predictions(df_hist: pd.DataFrame, df_current: pd.DataFrame) -> pd.DataFrame:
    preds = []

    df_hist_played = df_hist.dropna(subset=["FTHG", "FTAG"]).copy()
    if df_hist_played.empty or df_current.empty:
        return pd.DataFrame()

    teams = compute_team_strengths(df_hist_played)
    league_stats = df_hist_played.groupby("league").agg(
        avg_home_goals=("FTHG", "mean"),
        avg_away_goals=("FTAG", "mean"),
    ).reset_index()

    for _, row in df_current.iterrows():
        league = row["league"]
        home = row["HomeTeam"]
        away = row["AwayTeam"]

        if pd.isna(home) or pd.isna(away):
            continue

        ls = league_stats[league_stats["league"] == league]
        if ls.empty:
            continue

        lg = ls.iloc[0]
        avg_h = lg["avg_home_goals"]
        avg_a = lg["avg_away_goals"]

        ht_rows = teams[(teams["league"] == league) & (teams["team"] == home)]
        at_rows = teams[(teams["league"] == league) & (teams["team"] == away)]
        if ht_rows.empty or at_rows.empty:
            continue

        ht = ht_rows.iloc[0]
        at = at_rows.iloc[0]

        lam_home, lam_away = expected_goals_for_match(avg_h, avg_a, ht, at)
        probs_1x2 = match_probabilities_dc(lam_home, lam_away, rho=DC_RHO, max_goals=10)

        p_home = probs_1x2["p_home"]
        p_draw = probs_1x2["p_draw"]
        p_away = probs_1x2["p_away"]

        p_over25_poi, p_btts_poi = goal_market_probs(lam_home, lam_away, rho=DC_RHO, max_goals=10)

        if "Date" in row:
            match_date = row["Date"].date() if pd.notna(row["Date"]) else None
        else:
            match_date = None

        if pd.notna(row.get("FTHG")) and pd.notna(row.get("FTAG")):
            fthg = row["FTHG"]
            ftag = row["FTAG"]
            total_goals_real = fthg + ftag

            if fthg > ftag:
                actual = "H"
            elif fthg == ftag:
                actual = "D"
            else:
                actual = "A"

            actual_over25 = 1 if total_goals_real >= 3 else 0
            actual_btts = 1 if (fthg > 0 and ftag > 0) else 0

            is_fixture = False
        else:
            actual = None
            actual_over25 = None
            actual_btts = None
            is_fixture = True

        odd_home = row.get("B365H", np.nan)
        odd_draw = row.get("B365D", np.nan)
        odd_away = row.get("B365A", np.nan)

        book_over25 = row.get("B365>2.5", np.nan)
        book_under25 = row.get("B365<2.5", np.nan)

        book_btts_yes = row.get("BTSH", np.nan)
        book_btts_no = row.get("BTSD", np.nan)

        edge_home, kelly_home = compute_edge_and_kelly(p_home, odd_home)
        edge_draw, kelly_draw = compute_edge_and_kelly(p_draw, odd_draw)
        edge_away, kelly_away = compute_edge_and_kelly(p_away, odd_away)

        if is_fixture:
            model_pick = None
            hit = None
        else:
            if max(p_home, p_draw, p_away) == p_home:
                model_pick = "H"
            elif max(p_home, p_draw, p_away) == p_draw:
                model_pick = "D"
            else:
                model_pick = "A"
            hit = int(model_pick == actual) if actual is not None else None

        preds.append({
            "league": league,
            "match_date": match_date,
            "home": home,
            "away": away,
            "lambda_home": lam_home,
            "lambda_away": lam_away,
            "p_home": p_home,
            "p_draw": p_draw,
            "p_away": p_away,
            "fair_home": fair_odds(p_home),
            "fair_draw": fair_odds(p_draw),
            "fair_away": fair_odds(p_away),
            "book_home": odd_home,
            "book_draw": odd_draw,
            "book_away": odd_away,
            "edge_home": edge_home,
            "edge_draw": edge_draw,
            "edge_away": edge_away,
            "kelly_home": kelly_home,
            "kelly_draw": kelly_draw,
            "kelly_away": kelly_away,
            "p_over25_poi": p_over25_poi,
            "p_btts_poi": p_btts_poi,
            "book_over25": book_over25,
            "book_under25": book_under25,
            "book_btts_yes": book_btts_yes,
            "book_btts_no": book_btts_no,
            "actual": actual,
            "actual_over25": actual_over25,
            "actual_btts": actual_btts,
            "is_fixture": is_fixture,
            "model_pick": model_pick,
            "hit": hit,
        })

    return pd.DataFrame(preds)


# -------------------------------
# GOAL VALUE (AI) – EDGE & KELLY
# -------------------------------

def add_goal_value_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    edges_ou_ai = []
    kelly_ou_ai = []
    for _, r in df.iterrows():
        p = r.get("ai_p_over25")
        o = r.get("book_over25")
        edge, kelly = compute_edge_and_kelly(p, o)
        edges_ou_ai.append(edge)
        kelly_ou_ai.append(kelly)
    df["edge_ou25_ai"] = edges_ou_ai
    df["kelly_ou25_ai"] = kelly_ou_ai

    edges_btts_ai = []
    kelly_btts_ai = []
    for _, r in df.iterrows():
        p = r.get("ai_p_btts_yes")
        o = r.get("book_btts_yes")
        edge, kelly = compute_edge_and_kelly(p, o)
        edges_btts_ai.append(edge)
        kelly_btts_ai.append(kelly)
    df["edge_btts_ai"] = edges_btts_ai
    df["kelly_btts_ai"] = kelly_btts_ai

    return df

def add_recommended_and_risk(df: pd.DataFrame) -> pd.DataFrame:
    """
    Dodaje dvije kolone:
    - recommended_bet: tekst (npr. 'Home win (1)', 'Over 2.5', 'BTTS YES', 'No bet')
    - risk_level: 'HIGH' / 'MEDIUM' / 'LOW' / 'NONE'
    Logika: gleda najveći Kelly preko svih tržišta (1X2 + OU + BTTS).
    """
    df = df.copy()

    # Osiguraj da sve Kelly kolone postoje
    kelly_cols = [
        "kelly_home", "kelly_draw", "kelly_away",
        "kelly_ou25_ai", "kelly_btts_ai",
    ]
    for c in kelly_cols:
        if c not in df.columns:
            df[c] = 0.0
        df[c] = df[c].fillna(0.0)

    def row_logic(r):
        # map tržišta na Kelly
        k_map = {
            "H": r.get("kelly_home", 0.0),
            "D": r.get("kelly_draw", 0.0),
            "A": r.get("kelly_away", 0.0),
            "OU25": r.get("kelly_ou25_ai", 0.0),
            "BTTS": r.get("kelly_btts_ai", 0.0),
        }

        # najbolji Kelly
        best_key = max(k_map, key=lambda k: k_map[k])
        best_k = k_map[best_key]

        # ako nigdje nema pozitivnog Kellya → No bet
        if best_k <= 0:
            return pd.Series({"recommended_bet": "No bet", "risk_level": "NONE"})

        # map u tekst za korisnika
        if best_key == "H":
            rec = "Home win (1)"
        elif best_key == "D":
            rec = "Draw (X)"
        elif best_key == "A":
            rec = "Away win (2)"
        elif best_key == "OU25":
            rec = "Over 2.5 goals"
        elif best_key == "BTTS":
            rec = "BTTS YES"
        else:
            rec = "No bet"

        # risk level po jačini Kellya
        if best_k >= 0.05:
            risk = "HIGH"
        elif best_k >= 0.03:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        return pd.Series({"recommended_bet": rec, "risk_level": risk})

    extra = df.apply(row_logic, axis=1)
    df["recommended_bet"] = extra["recommended_bet"]
    df["risk_level"] = extra["risk_level"]

    return df


def build_pro_fixtures_excel(fixtures_dashboard: pd.DataFrame, season: str) -> BytesIO:
    """
    Radi PRO Excel s:
    - Fixtures_PRO sheet (sekcije, filteri, conditional formatting)
    - Best_Bets sheet (samo value betovi)
    - Info sheet (objašnjenja na engleskom)
    """
    buffer_fix = BytesIO()

    # Osiguraj da recommended_bet i risk_level postoje
    fixtures_dashboard = add_recommended_and_risk(fixtures_dashboard)

    with pd.ExcelWriter(buffer_fix, engine="openpyxl") as writer:
        # 🔹 VAŽNO: startrow=3 → header ide u row 4
        fixtures_dashboard.to_excel(
            writer,
            sheet_name="Fixtures_PRO",
            index=False,
            startrow=3
        )

        wb = writer.book
        ws = writer.sheets["Fixtures_PRO"]

        max_col = fixtures_dashboard.shape[1]
        last_col_letter = get_column_letter(max_col)

        # Title (row 1)
        title_cell = ws["A1"]
        ws.merge_cells(f"A1:{last_col_letter}1")
        title_cell.value = f"GOALMIND PRO – Fixtures (Poisson + AI + Kelly) {season}"
        title_cell.font = Font(bold=True, size=14)
        title_cell.alignment = Alignment(horizontal="center", vertical="center")

        # Subtitle (row 2)
        info_cell = ws["A2"]
        ws.merge_cells(f"A2:{last_col_letter}2")
        info_cell.value = "Expected goals (λ), Poisson & AI FT 1X2, AI goals (OU / BTTS), fair odds, edge & Kelly, recommended bet."
        info_cell.font = Font(size=10, italic=True)
        info_cell.alignment = Alignment(horizontal="center", vertical="center")

        col_names = list(fixtures_dashboard.columns)

        # SECTION HEADERS (row 3)
        section_row = 3
        header_row = 4  # 🟢 Ovdje su nazivi kolona iz DataFrame-a

        def cols_for(names):
            return [col_names.index(n) + 1 for n in names if n in col_names]

        sections = [
            ("Match info", cols_for(["league", "match_date", "home", "away"])),
            ("Signals", cols_for(["recommended_bet", "risk_level"])),
            ("Poisson FT 1X2", cols_for(["lambda_home", "lambda_away", "p_home", "p_draw", "p_away"])),
            ("AI FT 1X2", cols_for(["ai_p_home", "ai_p_draw", "ai_p_away"])),
            ("Poisson goals", cols_for(["p_over25_poi", "p_btts_poi"])),
            ("AI goals", cols_for(["ai_p_over25", "ai_p_btts_yes", "ai_total_goals"])),
            ("Odds", cols_for(["book_home", "book_draw", "book_away", "book_over25", "book_btts_yes"])),
            ("Edge & Kelly", cols_for([
                "edge_home", "edge_draw", "edge_away",
                "kelly_home", "kelly_draw", "kelly_away",
                "edge_ou25_ai", "kelly_ou25_ai",
                "edge_btts_ai", "kelly_btts_ai",
            ])),
        ]

        section_fill = PatternFill("solid", fgColor="E5E7EB")
        section_font = Font(bold=True)

        for label, cols_idx in sections:
            if not cols_idx:
                continue
            start_col = min(cols_idx)
            end_col = max(cols_idx)
            start_letter = get_column_letter(start_col)
            end_letter = get_column_letter(end_col)
            ws.merge_cells(f"{start_letter}{section_row}:{end_letter}{section_row}")
            cell = ws[f"{start_letter}{section_row}"]
            cell.value = label
            cell.font = section_font
            cell.fill = section_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Header styling (row 4 → pravi nazivi kolona)
        header_font = Font(bold=True)
        header_fill = PatternFill("solid", fgColor="CCCCCC")
        thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )

        for col_idx in range(1, max_col + 1):
            cell = ws.cell(row=header_row, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = thin_border
            cell.alignment = Alignment(horizontal="center", vertical="center")

            col_letter = get_column_letter(col_idx)
            header_name = col_names[col_idx - 1].lower()

            if col_letter in ["A", "B"]:
                ws.column_dimensions[col_letter].width = 14
            elif col_letter in ["C", "D"]:
                ws.column_dimensions[col_letter].width = 22
            elif header_name in ["recommended_bet", "risk_level"]:
                ws.column_dimensions[col_letter].width = 18
            else:
                ws.column_dimensions[col_letter].width = 12

        last_row = ws.max_row

        # Borders + alignment za sve podatke ispod headera
        for row_idx in range(header_row + 1, last_row + 1):
            for col_idx in range(1, max_col + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.border = thin_border
                if isinstance(cell.value, (int, float)):
                    cell.alignment = Alignment(horizontal="center", vertical="center")

        # Freeze header + filter
        ws.freeze_panes = ws["A5"]  # prva data row
        ws.auto_filter.ref = f"A{header_row}:{last_col_letter}{last_row}"

        # Conditional formatting – edges & Kelly
        edge_cols = [i + 1 for i, c in enumerate(col_names) if c.startswith("edge_")]
        kelly_cols = [i + 1 for i, c in enumerate(col_names) if c.startswith("kelly_")]

        green_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
        yellow_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")

        # Edge >= 0.05 -> green
        for col_idx in edge_cols:
            col_letter = get_column_letter(col_idx)
            rng = f"{col_letter}{header_row + 1}:{col_letter}{last_row}"
            ws.conditional_formatting.add(
                rng,
                CellIsRule(operator='greaterThanOrEqual', formula=['0.05'], fill=green_fill)
            )

        # Kelly >= 0.03 -> green, Kelly 0.015–0.03 -> yellow
        for col_idx in kelly_cols:
            col_letter = get_column_letter(col_idx)
            rng = f"{col_letter}{header_row + 1}:{col_letter}{last_row}"
            ws.conditional_formatting.add(
                rng,
                CellIsRule(operator='greaterThanOrEqual', formula=['0.03'], fill=green_fill)
            )
            ws.conditional_formatting.add(
                rng,
                CellIsRule(operator='between', formula=['0.015', '0.03'], fill=yellow_fill)
            )

        # ============== Best_Bets sheet ==============
        best_bets = fixtures_dashboard[
            (fixtures_dashboard["recommended_bet"] != "No bet") &
            (fixtures_dashboard["risk_level"].isin(["HIGH", "MEDIUM", "LOW"]))
        ].copy()

        if not best_bets.empty:
            risk_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0}
            best_bets["risk_order"] = best_bets["risk_level"].map(risk_order)
            kelly_cols_all = [c for c in best_bets.columns if c.startswith("kelly_")]
            best_bets["max_kelly_any"] = best_bets[kelly_cols_all].max(axis=1)
            best_bets = best_bets.sort_values(
                by=["risk_order", "max_kelly_any"], ascending=[False, False]
            )

            cols_best = [
                "league", "match_date", "home", "away",
                "recommended_bet", "risk_level",
                "p_home", "p_draw", "p_away",
                "ai_p_home", "ai_p_draw", "ai_p_away",
                "p_over25_poi", "ai_p_over25",
                "p_btts_poi", "ai_p_btts_yes",
                "book_home", "book_draw", "book_away",
                "book_over25", "book_btts_yes",
                "edge_home", "edge_draw", "edge_away",
                "edge_ou25_ai", "edge_btts_ai",
                "kelly_home", "kelly_draw", "kelly_away",
                "kelly_ou25_ai", "kelly_btts_ai",
            ]
            cols_best = [c for c in cols_best if c in best_bets.columns]

            best_bets[cols_best].to_excel(
                writer,
                sheet_name="Best_Bets",
                index=False,
                startrow=0
            )

            ws2 = writer.sheets["Best_Bets"]
            max_col2 = len(cols_best)
            last_col_letter2 = get_column_letter(max_col2)

            header_font2 = Font(bold=True)
            header_fill2 = PatternFill("solid", fgColor="D9E1F2")

            for col_idx in range(1, max_col2 + 1):
                cell = ws2.cell(row=1, column=col_idx)
                cell.font = header_font2
                cell.fill = header_fill2
                cell.border = thin_border
                cell.alignment = Alignment(horizontal="center", vertical="center")

                col_letter = get_column_letter(col_idx)
                name = cols_best[col_idx - 1].lower()
                if col_letter in ["A", "B"]:
                    ws2.column_dimensions[col_letter].width = 14
                elif col_letter in ["C", "D"]:
                    ws2.column_dimensions[col_letter].width = 22
                else:
                    ws2.column_dimensions[col_letter].width = 12

            last_row2 = ws2.max_row
            for row_idx in range(2, last_row2 + 1):
                for col_idx in range(1, max_col2 + 1):
                    cell = ws2.cell(row=row_idx, column=col_idx)
                    cell.border = thin_border
                    if isinstance(cell.value, (int, float)):
                        cell.alignment = Alignment(horizontal="center", vertical="center")

            ws2.auto_filter.ref = f"A1:{last_col_letter2}{last_row2}"
            ws2.freeze_panes = ws2["A2"]

        # ============== Info sheet ==============
        ws3 = wb.create_sheet("Info")

        ws3["A1"] = "GOALMIND PRO – Fixtures Excel"
        ws3["A1"].font = Font(bold=True, size=14)
        ws3["A3"] = "How to use this file:"
        ws3["A3"].font = Font(bold=True)

        ws3["A4"] = "- Sheet 'Fixtures_PRO': full fixtures table with Poisson, AI, odds, edge & Kelly and recommended bets."
        ws3["A5"] = "- Sheet 'Best_Bets': filtered shortlist of highest quality value bets."
        ws3["A6"] = "- Filters are already enabled on the header row – use them to filter by league, date, risk level, etc."
        ws3["A7"] = "- Green cells in edge/Kelly columns = strong value. Yellow cells = medium value (more risk)."

        ws3["A9"] = "Key columns:"
        ws3["A9"].font = Font(bold=True)

        explanations = [
            ("league", "League name (e.g., Championship, League One, Ligue 2...)."),
            ("match_date", "Match date (YYYY-MM-DD)."),
            ("home / away", "Home and away team names."),
            ("lambda_home / lambda_away", "Expected goals (xG-like Poisson λ) for each team."),
            ("p_home / p_draw / p_away", "Poisson+Dixon-Coles probability for FT 1X2."),
            ("ai_p_home / ai_p_draw / ai_p_away", "AI model probability for FT 1X2 (trained on multi-season data)."),
            ("p_over25_poi", "Poisson probability that total goals ≥ 3 (Over 2.5)."),
            ("p_btts_poi", "Poisson probability that both teams score (BTTS Yes)."),
            ("ai_p_over25", "AI probability for Over 2.5 goals."),
            ("ai_p_btts_yes", "AI probability for BTTS Yes."),
            ("ai_total_goals", "AI expected total goals (regression model)."),
            ("book_home / book_draw / book_away", "Market odds for FT 1X2 (B365 or similar)."),
            ("book_over25", "Market odds for Over 2.5 goals."),
            ("book_btts_yes", "Market odds for BTTS Yes."),
            ("edge_*", "Value indicator: edge = p * odds - 1. If > 0, model sees value."),
            ("kelly_*", "Kelly fraction for stake sizing. Typical use: stake = bank * Kelly * safety_factor."),
            ("recommended_bet", "Model suggestion: e.g. 'HOME', 'AWAY', 'Over 2.5', 'BTTS YES', or 'No bet'."),
            ("risk_level", "Risk profile of the recommended bet: LOW / MEDIUM / HIGH."),
        ]

        start_row = 11
        ws3["A10"] = "Column"
        ws3["B10"] = "Description"
        ws3["A10"].font = Font(bold=True)
        ws3["B10"].font = Font(bold=True)

        for i, (col_name, desc) in enumerate(explanations):
            r = start_row + i
            ws3[f"A{r}"] = col_name
            ws3[f"B{r}"] = desc

        ws3.column_dimensions["A"].width = 22
        ws3.column_dimensions["B"].width = 90

    buffer_fix.seek(0)
    return buffer_fix


# -------------------------------
# ROI HELPER FOR BINARY MARKETS
# -------------------------------

def compute_roi_binary(
    df: pd.DataFrame,
    prob_col: str,
    odds_col: str,
    actual_col: str,
    edge_threshold: float = 0.0
):
    """
    ROI for binary market (OU or BTTS) with flat stake = 1 unit.
    We bet only where p * odds - 1 > edge_threshold.
    Returns: (roi, number_of_bets)
    """
    d = df.copy()

    # moramo imati vjerojatnost, kvotu i stvarni ishod (0/1)
    d = d[
        d[prob_col].notna()
        & d[odds_col].notna()
        & d[actual_col].notna()
    ]

    if d.empty:
        return np.nan, 0

    # edge = p * odds - 1
    d["edge_tmp"] = d[prob_col] * d[odds_col] - 1.0
    d = d[d["edge_tmp"] > edge_threshold]

    if d.empty:
        return np.nan, 0

    # flat stake = 1
    d["profit"] = np.where(
        d[actual_col] == 1,
        d[odds_col] - 1.0,  # pogodak
        -1.0                # promašaj
    )

    total_profit = d["profit"].sum()
    n_bets = d.shape[0]
    roi = total_profit / n_bets

    return roi, n_bets
def render_landing_page():
    st.markdown("""
    <div style='text-align:center; padding: 15px 0;'>
        <h1 style='margin-bottom:0;'>⚡ GOALMIND PRO</h1>
        <p style='font-size:17px; color:#6b7280;'>Poisson • Dixon–Coles • AI • Kelly • Value Bets</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # HOW TO USE SECTION
    st.subheader("📘 How to Use GOALMIND PRO")

    st.markdown("""
    **GOALMIND PRO is built for bettors, analysts, and football data users who want fast, accurate and automated insights.  
    Follow this short guide to use it effectively:**

    ### 🔹 1. Overview (Main Dashboard)
    - See **overall accuracy** (Poisson vs AI)
    - See league summaries
    - Compare AI vs Poisson model performance  
    This tab gives the *global strength* of your system.

    ### 🔹 2. FT 1X2 Predictions
    - Poisson FT 1X2 probabilities  
    - AI FT 1X2 probabilities  
    - Fair odds and model confidence  
    **Use this tab to compare two systems and confirm the signal.**

    ### 🔹 3. Goals Predictions (OU & BTTS)
    - Poisson OU 2.5 and BTTS  
    - AI OU 2.5 and BTTS  
    - Combined xG prediction  
    **Great for totals bettors and over/under specialists.**

    ### 🔹 4. Fixtures & Value Bets
    - Upcoming fixtures  
    - Bookmaker odds (from Football-Data)  
    - Poisson + AI fair odds  
    - Edges (value) & Kelly stakes  
    - Automatic **Recommended Bet** + **Risk Level**  
    This is the main *money-making* tab.

    ### 🔹 5. Excel PRO Export
    - Generate a clean, professional Excel dashboard  
    - Includes:
        * Fixtures sheet  
        * Sections, filters, formatting  
        * Best Bets sheet  
        * Formulas and highlighting  
    Ideal if you sell the model or send results to clients.

    ---

    ### 💡 Tips for Best Use
    - Combine **AI + Poisson** → strongest confirmation  
    - Look for **edge ≥ 5%** (green cells)  
    - Use **Kelly ≥ 0.03** for medium/high confidence bets  
    - Follow only **LOW / MEDIUM / HIGH** rated picks  
    - Avoid “No Bet” matches unless manually reviewing xG & stats

    ---

    ### 🔒 Membership Access
    If you're seeing this screen, you already passed the login protection.  
    Share your Streamlit Cloud link to clients — they log in with password and get full access.

    ---

    ### 🧑‍💻 Support
    For issues or improvements, contact admin or send GitHub issue.
    """)

    st.markdown("---")

    st.markdown(
        "<p style='text-align:center; color:#9ca3af;'>© 2025 GOALMIND PRO – Football Predictions Engine</p>",
        unsafe_allow_html=True
    )


# -------------------------------
# STREAMLIT APP
# -------------------------------

def main():
    st.set_page_config(page_title="GOALMIND PRO – Poisson + AI", layout="wide")

    inject_pro_css()

    def main():
        st.set_page_config(page_title="GOALMIND PRO – Poisson + AI", layout="wide")

        inject_pro_css()

        # 🔹 OVDJE DODAJ:
        ensure_model_files()

        st.markdown(
            """
            <div class="hero">
                <div class="hero-title">⚡ GOALMIND PRO – Poisson + AI</div>
                <div class="hero-subtitle">
                    Multi-league model for FT 1X2, Over/Under 2.5 and BTTS with Poisson + AI + Kelly logic – ready for personal use or a PRO subscription service.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        ...

    st.markdown(
        """
        <div class="hero">
            <div class="hero-title">⚡ GOALMIND PRO – Poisson + AI</div>
            <div class="hero-subtitle">
                Multi-league model for FT 1X2, Over/Under 2.5 and BTTS with Poisson + AI + Kelly logic – ready for personal use or a PRO subscription service.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.title("⚙️ Model settings")
    season = st.sidebar.text_input("Season (football-data code)", value=DEFAULT_SEASON)
    selected_leagues = st.sidebar.multiselect(
        "Leagues",
        options=list(ALL_LEAGUES.keys()),
        default=list(ALL_LEAGUES.keys()),
    )

    min_edge = st.sidebar.slider("Min edge (FT 1X2)", 0.0, 0.2, 0.02, 0.005)
    min_kelly = st.sidebar.slider("Min Kelly (FT 1X2)", 0.0, 0.1, 0.01, 0.005)
    st.sidebar.markdown("---")
    st.sidebar.write("Data source: football-data.co.uk (history + fixtures)")

    # 1) History
    with st.spinner("Loading historical data (multi-season)..."):
        df_hist = load_all_leagues_multi(HISTORICAL_SEASONS)
        if df_hist.empty:
            st.error("No historical data found – check your files / connection.")
            return
        df_hist = df_hist[df_hist["league"].isin(selected_leagues)]

    # 2) Train goals AI if missing
    ensure_ai_goals_models(df_hist)

    # 3) Current season + fixtures
    with st.spinner("Loading current season and fixtures..."):
        df_curr = load_all_leagues(season)
        fixtures_web = load_fixtures_from_web()

        if not fixtures_web.empty:
            fixtures_web = fixtures_web[fixtures_web["league"].isin(selected_leagues)]
            df_curr = pd.concat([df_curr, fixtures_web], ignore_index=True)

        if not df_curr.empty:
            df_curr = df_curr[df_curr["league"].isin(selected_leagues)]

        if df_curr.empty:
            df_played_current = pd.DataFrame()
            df_fixtures_current = pd.DataFrame()
        else:
            df_played_current = df_curr.dropna(subset=["FTHG", "FTAG"]).copy()
            df_fixtures_current = df_curr[
                df_curr["FTHG"].isna()
                & df_curr["FTAG"].isna()
                & df_curr["HomeTeam"].notna()
                & df_curr["AwayTeam"].notna()
            ].copy()

        raw_fixtures_count = df_fixtures_current.shape[0]

        preds_played = generate_predictions(df_hist, df_played_current) if not df_played_current.empty else pd.DataFrame()
        preds_fixtures = generate_predictions(df_hist, df_fixtures_current) if not df_fixtures_current.empty else pd.DataFrame()

        if preds_played.empty and preds_fixtures.empty:
            st.warning("No predictions to display.")
            return
        elif preds_played.empty:
            preds = preds_fixtures.copy()
        elif preds_fixtures.empty:
            preds = preds_played.copy()
        else:
            preds = pd.concat([preds_played, preds_fixtures], ignore_index=True)

    # 4) AI FT 1X2 + AI goals + Kelly for goals
    preds = apply_ai_model(preds)
    preds = apply_ai_goals(preds)
    preds = add_goal_value_columns(preds)

    # ================= KPI & overview =================

    played_ft = preds[(preds["is_fixture"] == False) & (preds["actual"].notna())].copy()

    if not played_ft.empty:
        played_ft["poisson_pick"] = played_ft[["p_home", "p_draw", "p_away"]].idxmax(axis=1).map(
            {"p_home": "H", "p_draw": "D", "p_away": "A"}
        )
        played_ft["ai_pick"] = played_ft[["ai_p_home", "ai_p_draw", "ai_p_away"]].idxmax(axis=1).map(
            {"ai_p_home": "H", "ai_p_draw": "D", "ai_p_away": "A"}
        )
        played_ft["hit_poisson"] = (played_ft["poisson_pick"] == played_ft["actual"]).astype(int)
        played_ft["hit_ai"] = (played_ft["ai_pick"] == played_ft["actual"]).astype(int)
        acc_poi_ft = played_ft["hit_poisson"].mean()
        acc_ai_ft = played_ft["hit_ai"].mean()
    else:
        acc_poi_ft = np.nan
        acc_ai_ft = np.nan

    # Goals – accuracy
    played_goals = preds[(preds["is_fixture"] == False) & (preds["actual_over25"].notna())].copy()
    if not played_goals.empty and "ai_p_over25" in played_goals.columns:
        played_goals["poi_over25_pick"] = (played_goals["p_over25_poi"] >= 0.5).astype(int)
        played_goals["ai_over25_pick"] = (played_goals["ai_p_over25"] >= 0.5).astype(int)
        played_goals["hit_poi_over25"] = (played_goals["poi_over25_pick"] == played_goals["actual_over25"]).astype(int)
        played_goals["hit_ai_over25"] = (played_goals["ai_over25_pick"] == played_goals["actual_over25"]).astype(int)
        acc_poi_ou = played_goals["hit_poi_over25"].mean()
        acc_ai_ou = played_goals["hit_ai_over25"].mean()

        played_btts = played_goals[played_goals["actual_btts"].notna()].copy()
        if not played_btts.empty and "ai_p_btts_yes" in played_btts.columns:
            played_btts["poi_btts_pick"] = (played_btts["p_btts_poi"] >= 0.5).astype(int)
            played_btts["ai_btts_pick"] = (played_btts["ai_p_btts_yes"] >= 0.5).astype(int)
            played_btts["hit_poi_btts"] = (played_btts["poi_btts_pick"] == played_btts["actual_btts"]).astype(int)
            played_btts["hit_ai_btts"] = (played_btts["ai_btts_pick"] == played_btts["actual_btts"]).astype(int)
            acc_poi_btts = played_btts["hit_poi_btts"].mean()
            acc_ai_btts = played_btts["hit_ai_btts"].mean()
        else:
            acc_poi_btts = np.nan
            acc_ai_btts = np.nan
    else:
        acc_poi_ou = np.nan
        acc_ai_ou = np.nan
        acc_poi_btts = np.nan
        acc_ai_btts = np.nan

    # Goals – ROI (simple backtest)
    if not played_goals.empty:
        roi_poi_ou, n_poi_ou = compute_roi_binary(
            played_goals, prob_col="p_over25_poi", odds_col="book_over25",
            actual_col="actual_over25", edge_threshold=0.0
        )
        roi_ai_ou, n_ai_ou = compute_roi_binary(
            played_goals, prob_col="ai_p_over25", odds_col="book_over25",
            actual_col="actual_over25", edge_threshold=0.0
        )
        roi_poi_btts, n_poi_btts = compute_roi_binary(
            played_goals, prob_col="p_btts_poi", odds_col="book_btts_yes",
            actual_col="actual_btts", edge_threshold=0.0
        )
        roi_ai_btts, n_ai_btts = compute_roi_binary(
            played_goals, prob_col="ai_p_btts_yes", odds_col="book_btts_yes",
            actual_col="actual_btts", edge_threshold=0.0
        )
    else:
        roi_poi_ou = roi_ai_ou = roi_poi_btts = roi_ai_btts = np.nan
        n_poi_ou = n_ai_ou = n_poi_btts = n_ai_btts = 0

    num_leagues = len(preds["league"].unique())
    total_matches = len(preds)
    fixtures_count = preds[preds["is_fixture"] == True].shape[0]

    acc_ai_ft_str = f"{acc_ai_ft:.1%}" if not np.isnan(acc_ai_ft) else "N/A"
    acc_ai_ou_str = f"{acc_ai_ou:.1%}" if not np.isnan(acc_ai_ou) else "N/A"
    acc_ai_btts_str = f"{acc_ai_btts:.1%}" if not np.isnan(acc_ai_btts) else "N/A"

    roi_ai_ou_str = f"{roi_ai_ou*100:.1f}%" if not np.isnan(roi_ai_ou) else "N/A"
    roi_ai_btts_str = f"{roi_ai_btts*100:.1f}%" if not np.isnan(roi_ai_btts) else "N/A"

    # KPI cards – top row
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"""
            <div class="kpi-card">
              <div class="kpi-label">Leagues</div>
              <div class="kpi-main">{num_leagues}</div>
              <div class="kpi-sub">Active in the model</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="kpi-card">
              <div class="kpi-label">Matches (history + fixtures)</div>
              <div class="kpi-main">{total_matches}</div>
              <div class="kpi-sub">Total matches in dataset</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""
            <div class="kpi-card">
              <div class="kpi-label">Fixtures (upcoming)</div>
              <div class="kpi-main">{fixtures_count}</div>
              <div class="kpi-sub">Ready for betting</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"""
            <div class="kpi-card">
              <div class="kpi-label">AI FT 1X2 accuracy</div>
              <div class="kpi-main">{acc_ai_ft_str}</div>
              <div class="kpi-sub">On played matches</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # KPI cards – goals row
    g1, g2, g3, g4 = st.columns(4)
    with g1:
        st.markdown(
            f"""
            <div class="kpi-card">
              <div class="kpi-label">AI OU 2.5 accuracy</div>
              <div class="kpi-main">{acc_ai_ou_str}</div>
              <div class="kpi-sub">Over/Under 2.5 goals</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with g2:
        st.markdown(
            f"""
            <div class="kpi-card">
              <div class="kpi-label">AI BTTS accuracy</div>
              <div class="kpi-main">{acc_ai_btts_str}</div>
              <div class="kpi-sub">Both Teams To Score</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with g3:
        st.markdown(
            f"""
            <div class="kpi-card">
              <div class="kpi-label">AI OU 2.5 ROI (flat stake)</div>
              <div class="kpi-main">{roi_ai_ou_str}</div>
              <div class="kpi-sub">Conceptual backtest, no fees</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with g4:
        st.markdown(
            f"""
            <div class="kpi-card">
              <div class="kpi-label">AI BTTS ROI (flat stake)</div>
              <div class="kpi-main">{roi_ai_btts_str}</div>
              <div class="kpi-sub">Conceptual backtest, no fees</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Tabs – dodali smo LANDING kao prvi tab
    tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔑 Landing & Pricing",
        "🏠 Overview",
        "🎯 FT 1X2 (details)",
        "🥅 Goals OU/BTTS (details)",
        "🔮 Fixtures & value bets",
        "📥 Excel export",
    ])


    # TAB 0 – Landing & pricing
    with tab0:
        render_landing_page()

    # TAB 1 – Overview
    with tab1:
        st.subheader("Model overview – FT 1X2 and goals")

        c1_over, c2_over = st.columns(2)
        with c1_over:
            st.markdown("#### FT 1X2 – Poisson vs AI")
            if played_ft.empty:
                st.info("No played matches available for FT 1X2 analysis.")
            else:
                st.write(f"**Poisson FT 1X2 accuracy:** {acc_poi_ft:.1%}")
                st.write(f"**AI FT 1X2 accuracy:** {acc_ai_ft:.1%}")
                same_pick_ratio = (played_ft["poisson_pick"] == played_ft["ai_pick"]).mean()
                st.caption(f"Share of matches where Poisson and AI give the same pick: {same_pick_ratio:.1%}")

        with c2_over:
            st.markdown("#### Goals – OU 2.5 & BTTS")
            if np.isnan(acc_ai_ou):
                st.info("Not enough data for goals analysis.")
            else:
                st.write(f"**OU 2.5 – Poisson:** {acc_poi_ou:.1%} | **AI:** {acc_ai_ou:.1%}")
                if not np.isnan(acc_poi_btts) and not np.isnan(acc_ai_btts):
                    st.write(f"**BTTS – Poisson:** {acc_poi_btts:.1%} | **AI:** {acc_ai_btts:.1%}")
                elif not np.isnan(acc_poi_btts):
                    st.write(f"**BTTS – Poisson:** {acc_poi_btts:.1%} | **AI:** N/A")
                elif not np.isnan(acc_ai_btts):
                    st.write(f"**BTTS – Poisson:** N/A | **AI:** {acc_ai_btts:.1%}")
                else:
                    st.write("**BTTS – Poisson:** N/A | **AI:** N/A")

                if not np.isnan(roi_ai_ou):
                    st.write(f"**AI OU 2.5 ROI (flat 1u, edge>0):** {roi_ai_ou*100:.1f}% (bets: {n_ai_ou})")
                if not np.isnan(roi_ai_btts):
                    st.write(f"**AI BTTS ROI (flat 1u, edge>0):** {roi_ai_btts*100:.1f}% (bets: {n_ai_btts})")

        st.markdown("#### λ distribution (expected goals)")
        cc1, cc2 = st.columns(2)
        with cc1:
            st.caption("λ home")
            st.bar_chart(preds["lambda_home"])
        with cc2:
            st.caption("λ away")
            st.bar_chart(preds["lambda_away"])

    # TAB 2 – FT 1X2 details
    with tab2:
        st.subheader("FT 1X2 – detailed Poisson vs AI comparison")

        if played_ft.empty:
            st.info("No played matches available.")
        else:
            show_cols = [
                "league", "match_date", "home", "away",
                "actual", "poisson_pick", "ai_pick",
                "hit_poisson", "hit_ai",
                "p_home", "p_draw", "p_away",
                "ai_p_home", "ai_p_draw", "ai_p_away",
                "book_home", "book_draw", "book_away",
                "edge_home", "edge_draw", "edge_away",
                "kelly_home", "kelly_draw", "kelly_away",
            ]
            show_cols = [c for c in show_cols if c in played_ft.columns]
            st.dataframe(played_ft[show_cols].round(3), width="stretch")

    # TAB 3 – Goals details
    with tab3:
        st.subheader("Goals – OU 2.5 & BTTS (Poisson vs AI + ROI)")

        if played_goals.empty or "ai_p_over25" not in played_goals.columns:
            st.info("Not enough data for goals analysis.")
        else:
            c1_goals, c2_goals = st.columns(2)
            c1_goals.metric("OU 2.5 – Poisson accuracy", f"{acc_poi_ou:.1%}")
            c2_goals.metric("OU 2.5 – AI accuracy", f"{acc_ai_ou:.1%}")

            c3_goals, c4_goals = st.columns(2)
            if not np.isnan(acc_poi_btts):
                c3_goals.metric("BTTS – Poisson accuracy", f"{acc_poi_btts:.1%}")
                c4_goals.metric("BTTS – AI accuracy", f"{acc_ai_btts:.1%}")
            else:
                c3_goals.metric("BTTS – Poisson accuracy", "N/A")
                c4_goals.metric("BTTS – AI accuracy", "N/A")

            st.markdown("#### ROI simulation (flat 1u stake, bet where p·odds - 1 > 0)")

            r1, r2 = st.columns(2)
            if not np.isnan(roi_poi_ou):
                r1.metric("OU 2.5 – Poisson ROI", f"{roi_poi_ou*100:.1f}%", help=f"#bets: {n_poi_ou}")
            else:
                r1.metric("OU 2.5 – Poisson ROI", "N/A")

            if not np.isnan(roi_ai_ou):
                r2.metric("OU 2.5 – AI ROI", f"{roi_ai_ou*100:.1f}%", help=f"#bets: {n_ai_ou}")
            else:
                r2.metric("OU 2.5 – AI ROI", "N/A")

            r3, r4 = st.columns(2)
            if not np.isnan(roi_poi_btts):
                r3.metric("BTTS – Poisson ROI", f"{roi_poi_btts*100:.1f}%", help=f"#bets: {n_poi_btts}")
            else:
                r3.metric("BTTS – Poisson ROI", "N/A")

            if not np.isnan(roi_ai_btts):
                r4.metric("BTTS – AI ROI", f"{roi_ai_btts*100:.1f}%", help=f"#bets: {n_ai_btts}")
            else:
                r4.metric("BTTS – AI ROI", "N/A")

            # Profit chart for OU 2.5 (AI)
            st.markdown("#### Cumulative profit – AI OU 2.5 (flat 1u, edge>0)")
            ou_bets = played_goals[
                played_goals["ai_p_over25"].notna()
                & played_goals["book_over25"].notna()
                & played_goals["actual_over25"].notna()
            ].copy()
            ou_bets["edge_tmp"] = ou_bets["ai_p_over25"] * ou_bets["book_over25"] - 1.0
            ou_bets = ou_bets[ou_bets["edge_tmp"] > 0]
            if not ou_bets.empty:
                ou_bets = ou_bets.sort_values(["match_date", "league"]).reset_index(drop=True)
                ou_bets["profit"] = np.where(
                    ou_bets["actual_over25"] == 1,
                    ou_bets["book_over25"] - 1.0,
                    -1.0
                )
                ou_bets["cum_profit"] = ou_bets["profit"].cumsum()
                st.line_chart(ou_bets[["cum_profit"]])
            else:
                st.info("No AI OU 2.5 bets with edge>0 for profit chart.")

            # Profit chart for BTTS (AI)
            st.markdown("#### Cumulative profit – AI BTTS YES (flat 1u, edge>0)")
            btts_bets = played_goals[
                played_goals["ai_p_btts_yes"].notna()
                & played_goals["book_btts_yes"].notna()
                & played_goals["actual_btts"].notna()
            ].copy()
            btts_bets["edge_tmp"] = btts_bets["ai_p_btts_yes"] * btts_bets["book_btts_yes"] - 1.0
            btts_bets = btts_bets[btts_bets["edge_tmp"] > 0]
            if not btts_bets.empty:
                btts_bets = btts_bets.sort_values(["match_date", "league"]).reset_index(drop=True)
                btts_bets["profit"] = np.where(
                    btts_bets["actual_btts"] == 1,
                    btts_bets["book_btts_yes"] - 1.0,
                    -1.0
                )
                btts_bets["cum_profit"] = btts_bets["profit"].cumsum()
                st.line_chart(btts_bets[["cum_profit"]])
            else:
                st.info("No AI BTTS bets with edge>0 for profit chart.")

            st.markdown("#### Detailed table (played matches)")
            cols_show = [
                "league", "match_date", "home", "away",
                "actual_over25", "poi_over25_pick", "ai_over25_pick",
                "hit_poi_over25", "hit_ai_over25",
                "p_over25_poi", "ai_p_over25", "book_over25",
                "actual_btts", "p_btts_poi", "ai_p_btts_yes", "book_btts_yes",
                "ai_total_goals",
            ]
            cols_show = [c for c in cols_show if c in played_goals.columns]
            st.dataframe(played_goals[cols_show].round(3), width="stretch")

    # TAB 4 – Fixtures & value bets
    with tab4:
        st.subheader("Fixtures – FT 1X2 + Goals value bets")

        fixtures = preds[preds["is_fixture"] == True].copy()
        st.caption(f"Raw fixtures from web: {raw_fixtures_count} | Fixtures with model λ: {fixtures.shape[0]}")

        if fixtures.empty:
            st.warning("No fixture predictions to display.")
        else:
            cols_fix = [
                "league", "match_date", "home", "away",
                "lambda_home", "lambda_away",
                "p_home", "p_draw", "p_away",
                "ai_p_home", "ai_p_draw", "ai_p_away",
                "p_over25_poi", "p_btts_poi",
                "ai_p_over25", "ai_p_btts_yes",
                "ai_total_goals",
                "book_home", "book_draw", "book_away",
                "book_over25", "book_btts_yes",
                "edge_home", "edge_draw", "edge_away",
                "kelly_home", "kelly_draw", "kelly_away",
                "edge_ou25_ai", "kelly_ou25_ai",
                "edge_btts_ai", "kelly_btts_ai",
            ]
            cols_fix = [c for c in cols_fix if c in fixtures.columns]
            st.dataframe(fixtures[cols_fix].round(3), width="stretch")

            st.markdown("---")
            st.subheader("Top value bets – FT 1X2")

            rows_1x2 = []
            for _, r in fixtures.iterrows():
                for sel, p_col, odd_col, edge_col, kelly_col in [
                    ("H", "p_home", "book_home", "edge_home", "kelly_home"),
                    ("D", "p_draw", "book_draw", "edge_draw", "kelly_draw"),
                    ("A", "p_away", "book_away", "edge_away", "kelly_away"),
                ]:
                    p = r.get(p_col)
                    o = r.get(odd_col)
                    edge = r.get(edge_col)
                    kelly = r.get(kelly_col)
                    if (
                        p is not None and not np.isnan(p) and
                        o is not None and not np.isnan(o) and
                        edge is not None and not np.isnan(edge) and edge >= min_edge and
                        kelly is not None and kelly >= min_kelly
                    ):
                        rows_1x2.append({
                            "league": r["league"],
                            "match_date": r["match_date"],
                            "home": r["home"],
                            "away": r["away"],
                            "selection": sel,
                            "prob": p,
                            "odds": o,
                            "edge": edge,
                            "kelly": kelly,
                        })
            if rows_1x2:
                df_val_1x2 = pd.DataFrame(rows_1x2).sort_values("edge", ascending=False)
                st.dataframe(df_val_1x2.round(3), width="stretch")
            else:
                st.info("No FT 1X2 value bets for the current filters.")

            st.markdown("---")
            st.subheader("Top value bets – OU 2.5 (AI)")

            rows_ou = []
            for _, r in fixtures.iterrows():
                p = r.get("ai_p_over25")
                o = r.get("book_over25")
                edge = r.get("edge_ou25_ai")
                kelly = r.get("kelly_ou25_ai")
                if (
                    p is not None and not np.isnan(p) and
                    o is not None and not np.isnan(o) and
                    edge is not None and not np.isnan(edge) and edge >= 0.02 and
                    kelly is not None and kelly >= 0.01
                ):
                    rows_ou.append({
                        "league": r["league"],
                        "match_date": r["match_date"],
                        "home": r["home"],
                        "away": r["away"],
                        "selection": "Over 2.5",
                        "prob_ai": p,
                        "odds": o,
                        "edge_ai": edge,
                        "kelly_ai": kelly,
                    })
            if rows_ou:
                df_val_ou = pd.DataFrame(rows_ou).sort_values("edge_ai", ascending=False)
                st.dataframe(df_val_ou.round(3), width="stretch")
            else:
                st.info("No OU 2.5 AI value bets or no OU odds available.")

            st.markdown("---")
            st.subheader("Top value bets – BTTS YES (AI)")

            rows_btts = []
            for _, r in fixtures.iterrows():
                p = r.get("ai_p_btts_yes")
                o = r.get("book_btts_yes")
                edge = r.get("edge_btts_ai")
                kelly = r.get("kelly_btts_ai")
                if (
                    p is not None and not np.isnan(p) and
                    o is not None and not np.isnan(o) and
                    edge is not None and not np.isnan(edge) and edge >= 0.02 and
                    kelly is not None and kelly >= 0.01
                ):
                    rows_btts.append({
                        "league": r["league"],
                        "match_date": r["match_date"],
                        "home": r["home"],
                        "away": r["away"],
                        "selection": "BTTS YES",
                        "prob_ai": p,
                        "odds": o,
                        "edge_ai": edge,
                        "kelly_ai": kelly,
                    })
            if rows_btts:
                df_val_btts = pd.DataFrame(rows_btts).sort_values("edge_ai", ascending=False)
                st.dataframe(df_val_btts.round(3), width="stretch")
            else:
                st.info("No BTTS AI value bets or no BTTS odds available in the data.")

    # TAB 5 – Excel export
    with tab5:
        st.subheader("Excel export – all data + PRO fixtures")

        played = preds[preds["is_fixture"] == False].copy()
        fixtures = preds[preds["is_fixture"] == True].copy()

        fixtures_dashboard = pd.DataFrame()
        if not fixtures.empty:
            cols_fix = [
                "league", "match_date", "home", "away",
                "lambda_home", "lambda_away",
                "p_home", "p_draw", "p_away",
                "ai_p_home", "ai_p_draw", "ai_p_away",
                "p_over25_poi", "p_btts_poi",
                "ai_p_over25", "ai_p_btts_yes",
                "ai_total_goals",
                "book_home", "book_draw", "book_away",
                "book_over25", "book_btts_yes",
                "edge_home", "edge_draw", "edge_away",
                "kelly_home", "kelly_draw", "kelly_away",
                "edge_ou25_ai", "kelly_ou25_ai",
                "edge_btts_ai", "kelly_btts_ai",
            ]
            cols_fix = [c for c in cols_fix if c in fixtures.columns]
            fixtures_dashboard = fixtures[cols_fix].copy()
            prob_cols = [c for c in fixtures_dashboard.columns if c.startswith(("p_", "ai_p_"))]
            fixtures_dashboard[prob_cols] = fixtures_dashboard[prob_cols].round(3)

        buffer_all = BytesIO()
        with pd.ExcelWriter(buffer_all, engine="openpyxl") as writer:
            preds.to_excel(writer, index=False, sheet_name="Predictions_all")
            if not played.empty:
                played.to_excel(writer, index=False, sheet_name="Played_raw")
            if not fixtures.empty:
                fixtures.to_excel(writer, index=False, sheet_name="Fixtures_raw")
            if not fixtures_dashboard.empty:
                fixtures_dashboard.to_excel(writer, index=False, sheet_name="Fixtures_dashboard")
        buffer_all.seek(0)

        st.download_button(
            label="📥 Download FULL Excel (all tables)",
            data=buffer_all,
            file_name=f"poisson_ai_full_{season}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        st.markdown("---")
        st.subheader("📥 PRO Excel – Fixtures only (mini app for clients)")

        if fixtures_dashboard.empty:
            st.warning("No fixtures data available for PRO export.")
        else:
            buffer_fix = build_pro_fixtures_excel(fixtures_dashboard, season)
            st.download_button(
                label="📥 Download Fixtures PRO Excel",
                data=buffer_fix,
                file_name=f"fixtures_PRO_{season}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


if __name__ == "__main__":
    if check_password():
        main()

