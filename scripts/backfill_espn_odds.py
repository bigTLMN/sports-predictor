#!/usr/bin/env python3
"""Save 2025-26 DraftKings spreads and totals from ESPN game summaries.

The scoreboard drops odds after a game ends. The per-event summary still
has one DraftKings line. Regular season, play-in, and playoffs only.
"""

import argparse
import csv
import http.client
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scrape_teams import NBA_TEAM_IDS
STATS_PATH = ROOT / "data" / "TeamStatistics.csv"
OUT_PATH = ROOT / "data" / "odds_2025_26.csv"
KEEP_TYPES = {"Regular Season", "Playoffs", "Play-in Tournament"}
START = "2025-10-01"
END = "2026-06-30"
SCOREBOARD = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date}"
SUMMARY = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={event_id}"
FIELDS = [
    "gameId",
    "gameDate",
    "gameType",
    "homeTeamId",
    "awayTeamId",
    "espnEventId",
    "vegas_spread",
    "vegas_total",
    "spread_details",
    "provider",
]


def home_spread(details, home_abbr):
    """Home-perspective spread. Negative means the home team is favored."""
    text = (details or "").strip().upper()
    if text in {"EVEN", "PICK", "PK"}:
        return 0.0
    parts = text.split()
    if len(parts) < 2:
        return None
    favorite, raw = parts[0], parts[1]
    try:
        number = abs(float(raw))
    except ValueError:
        return None
    if favorite == home_abbr.upper():
        return -number
    return number


def fetch_json(url, pause=0.25, attempts=3):
    request = urllib.request.Request(url, headers={"User-Agent": "sports-predictor-odds-backfill"})
    last_error = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            time.sleep(pause)
            return payload
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            last_error = error
            time.sleep(1.5 * (attempt + 1))
        except (
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
            http.client.IncompleteRead,
            ConnectionError,
        ) as error:
            last_error = error
            time.sleep(1.5 * (attempt + 1))
    raise last_error


def load_games():
    games = {}
    with STATS_PATH.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("home") != "1":
                continue
            game_date = (row.get("gameDate") or row.get("gameDateTimeEst") or "")[:10]
            game_type = row.get("gameType") or ""
            if game_type not in KEEP_TYPES:
                continue
            if not (START <= game_date <= END):
                continue
            games[(game_date, int(row["teamId"]), int(row["opponentTeamId"]))] = {
                "gameId": row["gameId"],
                "gameDate": game_date,
                "gameType": game_type,
                "homeTeamId": int(row["teamId"]),
                "awayTeamId": int(row["opponentTeamId"]),
            }
    return games


def existing_ids():
    if not OUT_PATH.exists():
        return set()
    with OUT_PATH.open(newline="", encoding="utf-8") as handle:
        return {row["gameId"] for row in csv.DictReader(handle) if row.get("gameId")}


def draftkings_line(summary):
    books = summary.get("odds") or summary.get("pickcenter") or []
    if not books:
        return None
    def is_draftkings(book):
        name = ((book.get("provider") or {}).get("name") or "").replace(" ", "").lower()
        return name == "draftkings"

    chosen = next((book for book in books if is_draftkings(book)), books[0])
    return chosen


def append_row(row, write_header):
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def backfill(dates=None):
    games = load_games()
    done = existing_ids()
    pending = [game for game in games.values() if game["gameId"] not in done]
    if dates is not None:
        pending = [game for game in pending if game["gameDate"] in dates]
    by_date = {}
    for game in pending:
        by_date.setdefault(game["gameDate"], []).append(game)

    write_header = not OUT_PATH.exists() or OUT_PATH.stat().st_size == 0
    matched = 0
    missing_line = 0
    unmatched = []

    for index, game_date in enumerate(sorted(by_date), start=1):
        day_games = {(game["homeTeamId"], game["awayTeamId"]): game for game in by_date[game_date]}
        slate = fetch_json(SCOREBOARD.format(date=game_date.replace("-", "")))
        seen = set()
        for event in slate.get("events") or []:
            competition = event["competitions"][0]
            competitors = competition["competitors"]
            home = next(team for team in competitors if team.get("homeAway") == "home")
            away = next(team for team in competitors if team.get("homeAway") == "away")
            home_abbr = home["team"]["abbreviation"]
            away_abbr = away["team"]["abbreviation"]
            home_id = NBA_TEAM_IDS.get(home_abbr)
            away_id = NBA_TEAM_IDS.get(away_abbr)
            game = day_games.get((home_id, away_id))
            if game is None:
                continue
            seen.add((home_id, away_id))
            summary = fetch_json(SUMMARY.format(event_id=event["id"]))
            book = draftkings_line(summary) if summary else None
            spread = ""
            total = ""
            details = ""
            provider = ""
            if book:
                details = book.get("details") or ""
                provider = (book.get("provider") or {}).get("name") or ""
                parsed = home_spread(details, home_abbr)
                if parsed is not None:
                    spread = parsed
                total = book.get("overUnder")
                if total is None:
                    total = ""
            if spread == "" or total == "":
                missing_line += 1
            append_row(
                {
                    "gameId": game["gameId"],
                    "gameDate": game["gameDate"],
                    "gameType": game["gameType"],
                    "homeTeamId": game["homeTeamId"],
                    "awayTeamId": game["awayTeamId"],
                    "espnEventId": event["id"],
                    "vegas_spread": spread,
                    "vegas_total": total,
                    "spread_details": details,
                    "provider": provider,
                },
                write_header,
            )
            write_header = False
            matched += 1
        for key, game in day_games.items():
            if key not in seen:
                unmatched.append(game["gameId"])
        print(f"{index}/{len(by_date)} {game_date} matched {len(seen)}/{len(day_games)}", flush=True)

    print(f"matched {matched} missing_line {missing_line} unmatched {len(unmatched)}", flush=True)
    if unmatched:
        print("unmatched_ids " + ",".join(unmatched[:30]), flush=True)
    return matched, missing_line, unmatched


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dates", help="Comma-separated YYYY-MM-DD dates. Default is the whole season.")
    args = parser.parse_args()
    dates = None
    if args.dates:
        dates = {item.strip() for item in args.dates.split(",") if item.strip()}
    backfill(dates)


if __name__ == "__main__":
    main()
