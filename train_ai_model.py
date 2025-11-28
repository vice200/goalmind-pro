import os
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import requests
import joblib

from math import exp, factorial

from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# -------------------------------
# KONFIG
# -------------------------------

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
RAW_FOOTBALL_DIR = os.path.join("data", "raw", "football_data")
os.makedirs(RAW_FOOTBALL_DIR, exist_ok=True)

DC_RHO = 0.13

# -------------------------------
# DOWNLOAD & LOAD
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


def load_all_leagues_multi(seasons: List[str]) -> pd.DataFrame:
    all_dfs = []
    for season_code in seasons:
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
        raise RuntimeError("No historical data for AI goals.")

    combined = pd.concat(all_dfs, ignore_index=True)
    if "Date" in combined.columns:
        combined["Date"] = pd.to_datetime(combined["Date"], dayfirst=True, errors="coerce")
    else:
        combined["Date"] = pd.NaT

    return combined

# -------------------------------
# POISSON / DC – za feature-e
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


def goal_market_probs(lam_home: float, lam_away: float, rho: float = DC_RHO, max_goals: int = 10):
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
# TEAM STRENGTHS (isti princip kao u app.py)
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
# BUILD DATASET ZA GOALS AI
# -------------------------------

def build_goals_dataset(df_all: pd.DataFrame):
    df_played = df_all.dropna(subset=["FTHG", "FTAG"]).copy()

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

    X = pd.DataFrame(rows)
    X = X.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    y_over25 = pd.Series(y_over25, name="over25")
    y_btts = pd.Series(y_btts, name="btts")
    y_total_goals = pd.Series(y_total_goals, name="total_goals")

    feature_cols = list(X.columns)
    return X, y_over25, y_btts, y_total_goals, feature_cols

# -------------------------------
# MAIN – train i spremi modele
# -------------------------------

def main():
    print("[INFO] Loading multi-season data for AI goals...")
    df_all = load_all_leagues_multi(HISTORICAL_SEASONS)
    print(f"[INFO] Total matches (all seasons): {df_all.shape[0]}")

    print("[INFO] Building goals dataset...")
    X, y_over25, y_btts, y_total_goals, feature_cols = build_goals_dataset(df_all)
    print(f"[INFO] Dataset size: {len(X)} samples, {len(feature_cols)} features")

    # --- Over/Under 2.5 ---
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_over25, test_size=0.25, random_state=42, stratify=y_over25
    )
    over_model = RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        random_state=42,
        n_jobs=-1,
    )
    print("[INFO] Training RF model for Over/Under 2.5...")
    over_model.fit(X_train, y_train)
    y_pred = over_model.predict(X_test)
    acc_over = accuracy_score(y_test, y_pred)
    print(f"[RESULT] Over/Under 2.5 AI accuracy: {acc_over:.3f}")
    print(classification_report(y_test, y_pred))

    # --- BTTS ---
    X_train2, X_test2, y_train2, y_test2 = train_test_split(
        X, y_btts, test_size=0.25, random_state=42, stratify=y_btts
    )
    btts_model = RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        random_state=42,
        n_jobs=-1,
    )
    print("[INFO] Training RF model for BTTS...")
    btts_model.fit(X_train2, y_train2)
    y_pred2 = btts_model.predict(X_test2)
    acc_btts = accuracy_score(y_test2, y_pred2)
    print(f"[RESULT] BTTS AI accuracy: {acc_btts:.3f}")
    print(classification_report(y_test2, y_pred2))

    # --- total goals regressor ---
    X_train3, X_test3, y_train3, y_test3 = train_test_split(
        X, y_total_goals, test_size=0.25, random_state=42
    )
    goals_model = RandomForestRegressor(
        n_estimators=300,
        max_depth=12,
        random_state=42,
        n_jobs=-1,
    )
    print("[INFO] Training RF regressor for total goals expectancy...")
    goals_model.fit(X_train3, y_train3)
    y_pred3 = goals_model.predict(X_test3)
    mae = np.mean(np.abs(y_pred3 - y_test3))
    print(f"[RESULT] Total goals MAE: {mae:.3f}")

    os.makedirs("models", exist_ok=True)
    model_path = os.path.join("models", "ai_goals_models.pkl")
    joblib.dump(
        {
            "feature_cols": feature_cols,
            "over25_model": over_model,
            "btts_model": btts_model,
            "goals_model": goals_model,
        },
        model_path,
    )
    print(f"[OK] Goals AI models saved to: {model_path}")


if __name__ == "__main__":
    main()
