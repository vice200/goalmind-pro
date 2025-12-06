import pandas as pd
import glob
import os

# Uvozimo tvoju funkciju iz app.py – već tamo postoji
from app import load_all_leagues, DEFAULT_SEASON

XG_FOLDER = "data/api_football"


def collect_fd_teams():
    """Skupi sva imena klubova iz football-data (tvoj standardni model ulaz)."""
    df = load_all_leagues(DEFAULT_SEASON)
    teams = set(df["HomeTeam"].dropna().unique()) | set(df["AwayTeam"].dropna().unique())
    return pd.DataFrame(sorted(teams), columns=["fd_name"])


def collect_xg_teams():
    """Skupi sva imena klubova iz API-Football xG fajlova."""
    rows = []
    for path in glob.glob(os.path.join(XG_FOLDER, "*.xlsx")):
        df = pd.read_excel(path)
        # očekujemo "HomeTeam" i "AwayTeam" kao što smo radili u xg_outputu
        home_col = None
        away_col = None

        for cand in ["HomeTeam", "home_team_name", "Domacin", "home"]:
            if cand in df.columns:
                home_col = cand
                break

        for cand in ["AwayTeam", "away_team_name", "Gost", "away"]:
            if cand in df.columns:
                away_col = cand
                break

        if home_col is None or away_col is None:
            continue

        rows.extend(df[home_col].dropna().unique().tolist())
        rows.extend(df[away_col].dropna().unique().tolist())

    rows = sorted(set(rows))
    return pd.DataFrame(rows, columns=["api_name"])


def normalize(s: str) -> str:
    s = str(s).lower()
    repl = {
        ".": "",
        "-": " ",
        "_": " ",
        " fc": "",
        " cf": "",
        " ac": "",
        "  ": " ",
    }
    for k, v in repl.items():
        s = s.replace(k, v)
    return " ".join(s.split())


def generate_mapping():
    fd = collect_fd_teams()
    api = collect_xg_teams()

    print(f"[INFO] Football-Data teams: {len(fd)}")
    print(f"[INFO] API-Football teams: {len(api)}")

    mapping = fd.copy()
    mapping["api_match"] = ""

    fd_norm = {normalize(x): x for x in fd["fd_name"]}
    api_norm = {normalize(x): x for x in api["api_name"]}

    # automatski pokušaj match-a
    for norm_fd, original_fd in fd_norm.items():
        if norm_fd in api_norm:
            mapping.loc[mapping["fd_name"] == original_fd, "api_match"] = api_norm[norm_fd]

    # spremi za ručno uređivanje
    out_path = "team_mapping.xlsx"
    mapping.to_excel(out_path, index=False)
    print(f"✔ team_mapping.xlsx generated at {out_path}")
    print("→ Otvori u Excelu i ispuni 'api_match' gdje je prazno.")


if __name__ == "__main__":
    generate_mapping()
