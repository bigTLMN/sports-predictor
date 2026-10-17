import requests

import sqlite_store

ESPN_NBA_TEAMS_URL = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams"

NBA_TEAM_IDS = {
    "ATL": 1610612737,
    "BOS": 1610612738,
    "BKN": 1610612751,
    "CHA": 1610612766,
    "CHI": 1610612741,
    "CLE": 1610612739,
    "DAL": 1610612742,
    "DEN": 1610612743,
    "DET": 1610612765,
    "GSW": 1610612744,
    "HOU": 1610612745,
    "IND": 1610612754,
    "LAC": 1610612746,
    "LAL": 1610612747,
    "MEM": 1610612763,
    "MIA": 1610612748,
    "MIL": 1610612749,
    "MIN": 1610612750,
    "NOP": 1610612740,
    "NYK": 1610612752,
    "OKC": 1610612760,
    "ORL": 1610612753,
    "PHI": 1610612755,
    "PHX": 1610612756,
    "POR": 1610612757,
    "SAC": 1610612758,
    "SAS": 1610612759,
    "TOR": 1610612761,
    "UTA": 1610612762,
    "WAS": 1610612764,
    "WSH": 1610612764,
}


def store_teams(conn, raw_teams):
    count = 0
    for item in raw_teams:
        info = item["team"]
        code = info.get("abbreviation")
        nba_id = NBA_TEAM_IDS.get(code)
        if not code or nba_id is None:
            continue
        logos = info.get("logos") or [{}]
        sqlite_store.upsert_team(
            conn,
            code,
            info.get("shortDisplayName"),
            info.get("displayName"),
            logos[0].get("href") if logos else None,
            nba_id,
        )
        count += 1
    return count


def fetch_and_store_teams():
    conn = sqlite_store.connect()
    response = requests.get(ESPN_NBA_TEAMS_URL, timeout=30)
    response.raise_for_status()
    raw = response.json().get("sports", [])[0].get("leagues", [])[0].get("teams", [])
    count = store_teams(conn, raw)
    print(f"stored {count} teams")


if __name__ == "__main__":
    fetch_and_store_teams()
