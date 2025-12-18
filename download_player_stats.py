import os
import datetime
from typing import Dict, List

import requests
import pandas as pd
import numpy as np

# ==============================
# KONFIG
# ==============================

# 1) API KEY – ili iz env var ili direktno tu:
API_KEY = os.getenv("API_FOOTBALL_KEY") or "a7eebf46570faf8f72666659a8f0dfd9"  # ili stavi ovdje direktno string

BASE_URL = "https://v3.football.api-sports.io"

# 2) Lige (Football-Data kod → (API-Football league_id, ime))
LEAGUES: Dict[str, dict] = {
    "E0": {"id": 39, "name": "Premier League"},
    "E1": {"id": 40, "name": "Championship"},
    "E2": {"id": 41, "name": "League One"},
    "E3": {"id": 42, "name": "League Two"},
    "EC": {"id": 45, "name": "National League"},

    "SC0": {"id": 179, "name": "Scotland Premier"},
    "SC1": {"id": 180, "name": "Scotland Championship"},
    "SC2": {"id": 181, "name": "Scotland League One"},
    "SC3": {"id": 182, "name": "Scotland League Two"},

    "SP1": {"id": 140, "name": "La Liga"},
    "SP2": {"id": 141, "name": "La Liga 2"},

    "IT1": {"id": 135, "name": "Serie A"},
    "IT2": {"id": 136, "name": "Serie B"},

    "FR1": {"id": 61, "name": "Ligue 1"},
    "FR2": {"id": 62, "name": "Ligue 2"},

    "NL1": {"id": 88, "name": "Eredivisie"},
    "NL2": {"id": 89, "name": "Eerste Divisie"},

    "BE1": {"id": 144, "name": "Jupiler Pro League"},
    "PO1": {"id": 94, "name": "Primeira Liga"},
    "GR1": {"id": 197, "name": "Super League Greece"},
    "TU1": {"id": 203, "name": "Super Lig"},
    # "HR1": {"id": 387, "name": "1. HNL"},  # dodaš ako želiš
}

# 3) Sezona u API-Football formatu (godina početka sezone)
API_SEASON = 2025   # npr. 2025 za sezonu 2025/2026

# 4) Period oko današnjeg datuma
DAYS_BACK = 5   # koliko dana UNAZAD od danas
DAYS_AHEAD = 5  # koliko dana UNAPRIJED od danas


# ==============================
# HELPERI
# ==============================

def api_get(endpoint: str, params: dict) -> dict:
    """Jednostavan wrapper za GET prema API-Footballu."""
    if not API_KEY:
        raise RuntimeError("API_KEY nije postavljen. Stavi ga u kod ili u env var 'API_FOOTBALL_KEY'.")

    url = f"{BASE_URL}{endpoint}"
    headers = {
        "x-apisports-key": API_KEY,
        # ako koristiš RapidAPI, onda bi bilo:
        # "x-rapidapi-key": API_KEY,
        # "x-rapidapi-host": "v3.football.api-sports.io",
    }

    r = requests.get(url, headers=headers, params=params, timeout=30)
    try:
        data = r.json()
    except Exception:
        print(f"⚠ Ne mogu parsirati JSON za {endpoint} {params}, status={r.status_code}")
        return {"errors": {"http": r.status_code}, "response": []}

    errors = data.get("errors") or {}
    if errors:
        print(f"   ⚠ API error: {errors}")

    return data


def safe_float(x):
    try:
        if x is None or x == "":
            return np.nan
        return float(x)
    except Exception:
        return np.nan


def get_nested(d, *keys, default=None):
    """Sigurno dohvatiti ugniježđene ključeve iz dict-a."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        if k not in cur:
            return default
        cur = cur[k]
    return cur


# ==============================
# GLAVNI DIO
# ==============================

def main():
    today = datetime.date.today()
    from_date = today - datetime.timedelta(days=DAYS_BACK)
    to_date = today + datetime.timedelta(days=DAYS_AHEAD)

    from_str = from_date.strftime("%Y-%m-%d")
    to_str = to_date.strftime("%Y-%m-%d")

    print(f"Sezona (API-Football): {API_SEASON}")
    print(f"Period: {from_str} → {to_str}")
    print()

    all_rows: List[dict] = []

    for fd_code, info in LEAGUES.items():
        league_id = info["id"]
        league_name = info["name"]

        print(f"➡ Liga {fd_code} ({league_name}) – dohvaćam fixturee...")

        # 1) Dohvati fixturee u periodu [from, to]
        fixtures_data = api_get(
            "/fixtures",
            {
                "league": league_id,
                "season": API_SEASON,
                "from": from_str,
                "to": to_str,
                "timezone": "Europe/Zagreb",
            }
        )

        fixtures = fixtures_data.get("response", [])
        print(f"   Pronađeno utakmica: {len(fixtures)}")

        if not fixtures:
            print(f"   ⚠ Nema fixturea za ovaj period. Preskačem ligu.\n")
            continue

        # 2) Za svaku utakmicu zovi /fixtures/players?fixture=ID
        for fx in fixtures:
            fixture = fx.get("fixture", {})
            teams = fx.get("teams", {})

            fixture_id = fixture.get("id")
            date_str = fixture.get("date")
            round_name = fixture.get("round", "")

            home_name = get_nested(teams, "home", "name", default="")
            away_name = get_nested(teams, "away", "name", default="")

            # Pretvori datum
            try:
                match_date = pd.to_datetime(date_str)
            except Exception:
                match_date = pd.NaT

            if not fixture_id:
                continue

            print(f"   → Fixture {fixture_id}: {home_name} - {away_name} ({match_date}) – dohvaćam igrače...")

            players_data = api_get(
                "/fixtures/players",
                {
                    "fixture": fixture_id,
                }
            )

            players_resp = players_data.get("response", [])
            if not players_resp:
                print("      ⚠ Nema player stats-a za ovaj fixture.")
                continue

            # Struktura: response = [ { team: {...}, players: [ {player: {...}, statistics: [ {...} ]}, ... ] }, ... ]
            for team_block in players_resp:
                team_info = team_block.get("team", {})
                team_id = team_info.get("id")
                team_name = team_info.get("name", "")

                for p in team_block.get("players", []):
                    player_info = p.get("player", {})
                    stats_list = p.get("statistics", [])
                    if not stats_list:
                        continue
                    stats = stats_list[0]  # najčešće jedan element

                    # Osnovni podaci o igraču
                    player_id = player_info.get("id")
                    player_name = player_info.get("name", "")
                    player_age = player_info.get("age")
                    player_nationality = player_info.get("nationality", "")

                    # Games / rating
                    minutes = get_nested(stats, "games", "minutes")
                    position = get_nested(stats, "games", "position", default="")
                    grid = get_nested(stats, "games", "grid", default="")
                    rating_raw = get_nested(stats, "games", "rating")
                    rating = safe_float(rating_raw)

                    # Shots
                    shots_total = get_nested(stats, "shots", "total")
                    shots_on = get_nested(stats, "shots", "on")

                    # Goals
                    goals_total = get_nested(stats, "goals", "total")
                    goals_conceded = get_nested(stats, "goals", "conceded")
                    assists = get_nested(stats, "goals", "assists")
                    saves = get_nested(stats, "goals", "saves")

                    # Passes
                    passes_total = get_nested(stats, "passes", "total")
                    passes_key = get_nested(stats, "passes", "key")
                    passes_accuracy = get_nested(stats, "passes", "accuracy")

                    # Tackles
                    tackles_total = get_nested(stats, "tackles", "total")
                    tackles_blocks = get_nested(stats, "tackles", "blocks")
                    tackles_interceptions = get_nested(stats, "tackles", "interceptions")

                    # Duels
                    duels_total = get_nested(stats, "duels", "total")
                    duels_won = get_nested(stats, "duels", "won")

                    # Dribbles
                    dribbles_attempts = get_nested(stats, "dribbles", "attempts")
                    dribbles_success = get_nested(stats, "dribbles", "success")

                    # Fouls
                    fouls_drawn = get_nested(stats, "fouls", "drawn")
                    fouls_committed = get_nested(stats, "fouls", "committed")

                    # Cards
                    yellow = get_nested(stats, "cards", "yellow")
                    yellow_red = get_nested(stats, "cards", "yellowred")
                    red = get_nested(stats, "cards", "red")

                    # Penalties
                    pen_won = get_nested(stats, "penalty", "won")
                    pen_committed = get_nested(stats, "penalty", "commited")  # da, API ima tipfeler :)
                    pen_scored = get_nested(stats, "penalty", "scored")
                    pen_missed = get_nested(stats, "penalty", "missed")
                    pen_saved = get_nested(stats, "penalty", "saved")

                    row = {
                        "fd_league": fd_code,
                        "api_league_id": league_id,
                        "league_name": league_name,
                        "fixture_id": fixture_id,
                        "round": round_name,
                        "match_date": match_date,
                        "home_team": home_name,
                        "away_team": away_name,

                        "team_id": team_id,
                        "team_name": team_name,

                        "player_id": player_id,
                        "player_name": player_name,
                        "player_age": player_age,
                        "player_nationality": player_nationality,

                        "position": position,
                        "grid": grid,
                        "minutes": minutes,

                        "rating_raw": rating_raw,
                        "rating": rating,

                        "shots_total": shots_total,
                        "shots_on": shots_on,

                        "goals_total": goals_total,
                        "goals_conceded": goals_conceded,
                        "assists": assists,
                        "saves": saves,

                        "passes_total": passes_total,
                        "passes_key": passes_key,
                        "passes_accuracy": passes_accuracy,

                        "tackles_total": tackles_total,
                        "tackles_blocks": tackles_blocks,
                        "tackles_interceptions": tackles_interceptions,

                        "duels_total": duels_total,
                        "duels_won": duels_won,

                        "dribbles_attempts": dribbles_attempts,
                        "dribbles_success": dribbles_success,

                        "fouls_drawn": fouls_drawn,
                        "fouls_committed": fouls_committed,

                        "yellow_cards": yellow,
                        "yellow_red_cards": yellow_red,
                        "red_cards": red,

                        "pen_won": pen_won,
                        "pen_committed": pen_committed,
                        "pen_scored": pen_scored,
                        "pen_missed": pen_missed,
                        "pen_saved": pen_saved,
                    }

                    all_rows.append(row)

        print(f"   ✅ Liga {fd_code} gotova.\n")

    # ==========================
    # ZAVRŠNO – SPREMI U EXCEL
    # ==========================
    if not all_rows:
        print("⚠ Nema nikakvih player stats-a u zadanom periodu (provjeri sezonu/period ili plan).")
        return

    df = pd.DataFrame(all_rows)

    # Makni timezone sa datetime kolona, ako postoji
    for col in df.select_dtypes(include=["datetimetz"]).columns:
        df[col] = df[col].dt.tz_localize(None)

    out_name = "api_football_player_stats.xlsx"
    df.to_excel(out_name, index=False)

    print(f"✅ Gotovo! Spremljeno u {out_name}")
    print(f"   Ukupno redova (igrač × utakmica): {df.shape[0]}")


if __name__ == "__main__":
    main()
