# Pi SQLite Snapshot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store NBA games, odds, and picks in SQLite on the Pi USB disk, and serve the Vercel site from a JSON snapshot on GitHub instead of Supabase.

**Architecture:** `sqlite_store.py` is the only database API. The existing scrape, grade, and predict scripts call it. `export_snapshot.py` writes `web-app/data/public-snapshot.json` before the current git commit. Next.js fetches that file from raw GitHub on each request. A 2GB ext4 image on `/mnt/usb` holds the database.

**Tech Stack:** Python 3 sqlite3, bash, Next.js fetch, ext4 loop mount.

## Global Constraints

- Do not rebuild the model, change `PREDICT_DAYS`, or add ATS backtesting.
- Do not format `/mnt/usb`. Do not put CSV or `.pkl` files inside the 2GB image.
- Do not create a public Pi URL and do not use a Cloudflare quick tunnel as the site data source.
- Do not restart other bots' systemd services.
- Do not edit `scrape_odds.py`.
- Leave `SUPABASE_URL` and `SUPABASE_KEY` in `.env`. Runtime code must not read them.
- Schedule stays every 30 minutes. Retrain only when Taipei hour is `22` and minute is `< 30`.
- `pi_update.sh` still prints `抓賽程`, `結算`, `跳過重訓` or `開始重訓`, and `預測`.
- Snapshot URL is `https://raw.githubusercontent.com/bigTLMN/sports-predictor/main/web-app/data/public-snapshot.json` with `cache: 'no-store'`.
- Push with `git push origin HEAD:main` from branch `pi-cron-pipeline`. Never force push.
- `teams.nba_team_id` is required even though the spec's column list omitted it. `aggregate_picks.py` reads `home_team.nba_team_id` for features. Store the ESPN abbreviation in `code` and the NBA id from the map in Task 2.
- Bash tests on the Pi must run with `env -u TMPDIR` because `/mnt/usb/scratch/tmp` is noexec.

Work only in `D:\sports-predictor\.worktrees\pi-cron-pipeline`.

---

### Task 1: SQLite schema and writes

**Files:**
- Create: `sqlite_store.py`
- Test: `tests/test_sqlite_store.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `connect(path: str | None = None) -> sqlite3.Connection` — uses `path` or env `NBA_SQLITE_PATH`. Does not create `/mnt/sports-db`.
  - `upsert_team(conn, code, name, full_name, logo_url, nba_team_id) -> int`
  - `upsert_match(conn, row: dict) -> int` — `period_scores` may be a dict; stored as JSON text. Lookup key is `date`, `home_team_id`, `away_team_id`.
  - `upsert_pick(conn, row: dict) -> int` — lookup key is `match_id`. Does not clear `spread_outcome` or `total_outcome` when those keys are absent.
  - `grade_pick(conn, pick_id: int, spread_outcome: str | None, total_outcome: str | None) -> None`
  - `export_snapshot(conn) -> dict` — keys `teams`, `matches`, `picks` as specified below.

- [ ] **Step 1: Write the failing test**

Create `tests/test_sqlite_store.py`:

```python
import json
import os
import tempfile
import unittest

os.environ["NBA_SQLITE_PATH"] = os.path.join(tempfile.mkdtemp(), "nba.sqlite")

import sqlite_store as store


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.conn = store.connect(os.environ["NBA_SQLITE_PATH"])

    def test_upsert_team_by_code(self):
        first = store.upsert_team(self.conn, "LAL", "Lakers", "Los Angeles Lakers", "http://logo", 1610612747)
        second = store.upsert_team(self.conn, "LAL", "Lakers", "Los Angeles Lakers", "http://logo2", 1610612747)
        self.assertEqual(first, second)
        row = self.conn.execute("SELECT logo_url, nba_team_id FROM teams WHERE code='LAL'").fetchone()
        self.assertEqual(row["logo_url"], "http://logo2")
        self.assertEqual(row["nba_team_id"], 1610612747)

    def test_upsert_match_keeps_one_row_and_json_periods(self):
        home = store.upsert_team(self.conn, "LAL", "Lakers", "Los Angeles Lakers", None, 1610612747)
        away = store.upsert_team(self.conn, "BOS", "Celtics", "Boston Celtics", None, 1610612738)
        row = {
            "date": "2026-10-18",
            "start_time": "2026-10-18T23:00:00Z",
            "home_team_id": home,
            "away_team_id": away,
            "status": "STATUS_SCHEDULED",
            "home_score": 0,
            "away_score": 0,
            "period_scores": {"home": [1], "away": [2]},
            "vegas_spread": -3.5,
            "vegas_total": 220.5,
        }
        match_id = store.upsert_match(self.conn, row)
        row["home_score"] = 110
        row["status"] = "STATUS_FINISHED"
        again = store.upsert_match(self.conn, row)
        self.assertEqual(match_id, again)
        saved = self.conn.execute("SELECT home_score, period_scores FROM matches WHERE id=?", (match_id,)).fetchone()
        self.assertEqual(saved["home_score"], 110)
        self.assertEqual(json.loads(saved["period_scores"])["home"], [1])

    def test_upsert_pick_does_not_wipe_grades(self):
        home = store.upsert_team(self.conn, "LAL", "Lakers", "Los Angeles Lakers", None, 1)
        away = store.upsert_team(self.conn, "BOS", "Celtics", "Boston Celtics", None, 2)
        match_id = store.upsert_match(self.conn, {
            "date": "2026-10-18", "start_time": "2026-10-18T23:00:00Z",
            "home_team_id": home, "away_team_id": away, "status": "STATUS_FINISHED",
            "home_score": 110, "away_score": 100, "period_scores": None,
            "vegas_spread": -3.5, "vegas_total": 220.5,
        })
        pick_id = store.upsert_pick(self.conn, {
            "match_id": match_id, "recommended_team_id": home, "confidence_score": 60,
            "spread_logic": "en", "spread_logic_zh": "zh", "line_info": "-3.5",
            "ou_pick": "OVER", "ou_line": 220.5, "ou_confidence": 55,
            "analysis_content": "a", "analysis_content_zh": "甲",
            "predicted_margin": 4.0, "predicted_total": 225.0, "created_at": "2026-10-17T00:00:00",
        })
        store.grade_pick(self.conn, pick_id, "WIN", "LOSS")
        store.upsert_pick(self.conn, {
            "match_id": match_id, "recommended_team_id": home, "confidence_score": 61,
            "spread_logic": "en2", "spread_logic_zh": "zh2", "line_info": "-3.5",
            "ou_pick": "OVER", "ou_line": 220.5, "ou_confidence": 55,
            "analysis_content": "b", "analysis_content_zh": "乙",
            "predicted_margin": 5.0, "predicted_total": 226.0, "created_at": "2026-10-17T01:00:00",
        })
        graded = self.conn.execute(
            "SELECT spread_outcome, total_outcome, confidence_score FROM aggregated_picks WHERE id=?",
            (pick_id,),
        ).fetchone()
        self.assertEqual(graded["spread_outcome"], "WIN")
        self.assertEqual(graded["total_outcome"], "LOSS")
        self.assertEqual(graded["confidence_score"], 61)

    def test_export_snapshot_nests_teams(self):
        home = store.upsert_team(self.conn, "LAL", "Lakers", "Los Angeles Lakers", "h", 1)
        away = store.upsert_team(self.conn, "BOS", "Celtics", "Boston Celtics", "a", 2)
        match_id = store.upsert_match(self.conn, {
            "date": "2026-10-18", "start_time": "2026-10-18T23:00:00Z",
            "home_team_id": home, "away_team_id": away, "status": "STATUS_SCHEDULED",
            "home_score": 0, "away_score": 0, "period_scores": {"home": [], "away": []},
            "vegas_spread": -3.5, "vegas_total": 220.5,
        })
        store.upsert_pick(self.conn, {
            "match_id": match_id, "recommended_team_id": home, "confidence_score": 60,
            "spread_logic": "en", "spread_logic_zh": "zh", "line_info": "-3.5",
            "ou_pick": "OVER", "ou_line": 220.5, "ou_confidence": 55,
            "analysis_content": "a", "analysis_content_zh": "甲",
            "predicted_margin": 4.0, "predicted_total": 225.0, "created_at": "2026-10-17T00:00:00",
        })
        snap = store.export_snapshot(self.conn)
        self.assertEqual(set(snap), {"teams", "matches", "picks"})
        self.assertEqual(snap["matches"][0]["home_team"]["code"], "LAL")
        self.assertEqual(snap["matches"][0]["away_team"]["full_name"], "Boston Celtics")
        self.assertEqual(snap["picks"][0]["matches"]["home_team"]["logo_url"], "h")
        self.assertEqual(snap["picks"][0]["recommended_team"]["code"], "LAL")
        self.assertIsInstance(snap["matches"][0]["period_scores"], dict)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

```powershell
python -m unittest tests.test_sqlite_store -v
```

Run from `D:\sports-predictor\.worktrees\pi-cron-pipeline`. Expected: FAIL with `ModuleNotFoundError: sqlite_store`.

- [ ] **Step 3: Write `sqlite_store.py`**

```python
import json
import os
import sqlite3

DEFAULT_PATH = "/mnt/sports-db/nba.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS teams (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  name TEXT,
  full_name TEXT,
  logo_url TEXT,
  nba_team_id INTEGER
);
CREATE TABLE IF NOT EXISTS matches (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  start_time TEXT,
  home_team_id INTEGER NOT NULL,
  away_team_id INTEGER NOT NULL,
  status TEXT,
  home_score INTEGER,
  away_score INTEGER,
  period_scores TEXT,
  vegas_spread REAL,
  vegas_total REAL,
  UNIQUE(date, home_team_id, away_team_id)
);
CREATE TABLE IF NOT EXISTS aggregated_picks (
  id INTEGER PRIMARY KEY,
  match_id INTEGER NOT NULL UNIQUE,
  recommended_team_id INTEGER,
  confidence_score REAL,
  spread_logic TEXT,
  spread_logic_zh TEXT,
  line_info TEXT,
  ou_pick TEXT,
  ou_line REAL,
  ou_confidence REAL,
  analysis_content TEXT,
  analysis_content_zh TEXT,
  predicted_margin REAL,
  predicted_total REAL,
  spread_outcome TEXT,
  total_outcome TEXT,
  created_at TEXT
);
"""

PICK_FIELDS = (
    "recommended_team_id", "confidence_score", "spread_logic", "spread_logic_zh",
    "line_info", "ou_pick", "ou_line", "ou_confidence", "analysis_content",
    "analysis_content_zh", "predicted_margin", "predicted_total", "created_at",
)


def connect(path=None):
    db_path = path or os.environ.get("NBA_SQLITE_PATH", DEFAULT_PATH)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def upsert_team(conn, code, name, full_name, logo_url, nba_team_id):
    conn.execute(
        """
        INSERT INTO teams (code, name, full_name, logo_url, nba_team_id)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(code) DO UPDATE SET
          name=excluded.name,
          full_name=excluded.full_name,
          logo_url=excluded.logo_url,
          nba_team_id=excluded.nba_team_id
        """,
        (code, name, full_name, logo_url, nba_team_id),
    )
    conn.commit()
    return conn.execute("SELECT id FROM teams WHERE code=?", (code,)).fetchone()["id"]


def upsert_match(conn, row):
    periods = row.get("period_scores")
    periods_text = json.dumps(periods) if isinstance(periods, dict) else periods
    existing = conn.execute(
        "SELECT id FROM matches WHERE date=? AND home_team_id=? AND away_team_id=?",
        (row["date"], row["home_team_id"], row["away_team_id"]),
    ).fetchone()
    values = (
        row.get("start_time"), row.get("status"), row.get("home_score"), row.get("away_score"),
        periods_text, row.get("vegas_spread"), row.get("vegas_total"),
        row["date"], row["home_team_id"], row["away_team_id"],
    )
    if existing:
        conn.execute(
            """
            UPDATE matches SET start_time=?, status=?, home_score=?, away_score=?,
              period_scores=?, vegas_spread=?, vegas_total=?
            WHERE date=? AND home_team_id=? AND away_team_id=?
            """,
            values,
        )
        match_id = existing["id"]
    else:
        cur = conn.execute(
            """
            INSERT INTO matches (
              start_time, status, home_score, away_score, period_scores, vegas_spread, vegas_total,
              date, home_team_id, away_team_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
        match_id = cur.lastrowid
    conn.commit()
    return match_id


def upsert_pick(conn, row):
    existing = conn.execute(
        "SELECT id FROM aggregated_picks WHERE match_id=?", (row["match_id"],)
    ).fetchone()
    if existing:
        assignments = ", ".join(f"{field}=?" for field in PICK_FIELDS)
        conn.execute(
            f"UPDATE aggregated_picks SET {assignments} WHERE match_id=?",
            tuple(row.get(field) for field in PICK_FIELDS) + (row["match_id"],),
        )
        pick_id = existing["id"]
    else:
        columns = ("match_id",) + PICK_FIELDS
        placeholders = ", ".join("?" for _ in columns)
        cur = conn.execute(
            f"INSERT INTO aggregated_picks ({', '.join(columns)}) VALUES ({placeholders})",
            tuple(row.get(field) for field in columns),
        )
        pick_id = cur.lastrowid
    conn.commit()
    return pick_id


def grade_pick(conn, pick_id, spread_outcome, total_outcome):
    if spread_outcome is not None:
        conn.execute(
            "UPDATE aggregated_picks SET spread_outcome=? WHERE id=? AND spread_outcome IS NULL",
            (spread_outcome, pick_id),
        )
    if total_outcome is not None:
        conn.execute(
            "UPDATE aggregated_picks SET total_outcome=? WHERE id=? AND total_outcome IS NULL",
            (total_outcome, pick_id),
        )
    conn.commit()


def _team(conn, team_id):
    row = conn.execute(
        "SELECT id, code, name, full_name, logo_url, nba_team_id FROM teams WHERE id=?",
        (team_id,),
    ).fetchone()
    return dict(row) if row else None


def _public_team(team):
    if not team:
        return None
    return {"code": team["code"], "full_name": team["full_name"], "logo_url": team["logo_url"]}


def _match_public(conn, row):
    data = dict(row)
    raw = data.get("period_scores")
    if isinstance(raw, str) and raw:
        data["period_scores"] = json.loads(raw)
    home = _team(conn, data["home_team_id"])
    away = _team(conn, data["away_team_id"])
    data["home_team"] = _public_team(home)
    data["away_team"] = _public_team(away)
    data["home_team_nba_id"] = home["nba_team_id"] if home else None
    data["away_team_nba_id"] = away["nba_team_id"] if away else None
    return data


def export_snapshot(conn):
    teams = [dict(row) for row in conn.execute("SELECT id, code, name, full_name, logo_url, nba_team_id FROM teams ORDER BY id")]
    matches = [
        _match_public(conn, row)
        for row in conn.execute("SELECT * FROM matches ORDER BY start_time, id")
    ]
    picks = []
    for row in conn.execute("SELECT * FROM aggregated_picks ORDER BY id"):
        pick = dict(row)
        match = conn.execute("SELECT * FROM matches WHERE id=?", (pick["match_id"],)).fetchone()
        pick["matches"] = _match_public(conn, match) if match else None
        rec = _team(conn, pick["recommended_team_id"])
        pick["recommended_team"] = {"code": rec["code"], "logo_url": rec["logo_url"]} if rec else None
        picks.append(pick)
    return {"teams": teams, "matches": matches, "picks": picks}
```

- [ ] **Step 4: Run the test to verify it passes**

```powershell
python -m unittest tests.test_sqlite_store -v
```

Expected: 4 tests, all OK.

- [ ] **Step 5: Commit**

```powershell
git -C "D:\sports-predictor\.worktrees\pi-cron-pipeline" add -- sqlite_store.py tests/test_sqlite_store.py
git -C "D:\sports-predictor\.worktrees\pi-cron-pipeline" commit -m "feat: add the SQLite store for games and picks"
```

Do not push yet.

---

### Task 2: Seed teams from ESPN

**Files:**
- Modify: `scrape_teams.py`
- Test: `tests/test_scrape_teams.py`

**Interfaces:**
- Consumes: `connect`, `upsert_team`
- Produces: `NBA_TEAM_IDS` dict keyed by ESPN abbreviation, and `store_teams(conn, raw_teams: list) -> int`

- [ ] **Step 1: Write the failing test**

```python
import os
import tempfile
import unittest

os.environ["NBA_SQLITE_PATH"] = os.path.join(tempfile.mkdtemp(), "nba.sqlite")

import scrape_teams
import sqlite_store


class TeamSeedTests(unittest.TestCase):
    def test_store_teams_uses_espn_abbreviation_and_nba_id(self):
        conn = sqlite_store.connect(os.environ["NBA_SQLITE_PATH"])
        count = scrape_teams.store_teams(conn, [{
            "team": {
                "abbreviation": "LAL",
                "shortDisplayName": "Lakers",
                "displayName": "Los Angeles Lakers",
                "logos": [{"href": "http://logo"}],
            }
        }])
        self.assertEqual(count, 1)
        row = conn.execute("SELECT code, nba_team_id, full_name FROM teams").fetchone()
        self.assertEqual(row["code"], "LAL")
        self.assertEqual(row["nba_team_id"], 1610612747)
        self.assertEqual(row["full_name"], "Los Angeles Lakers")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it and confirm FAIL** because `store_teams` does not exist.

```powershell
python -m unittest tests.test_scrape_teams -v
```

- [ ] **Step 3: Replace `scrape_teams.py`**

Keep the ESPN URL. Remove Supabase and the leagues lookup. Add `NBA_TEAM_IDS` for all 30 abbreviations: ATL 1610612737, BOS 1610612738, BKN 1610612751, CHA 1610612766, CHI 1610612741, CLE 1610612739, DAL 1610612742, DEN 1610612743, DET 1610612765, GSW 1610612744, HOU 1610612745, IND 1610612754, LAC 1610612746, LAL 1610612747, MEM 1610612763, MIA 1610612748, MIL 1610612749, MIN 1610612750, NOP 1610612740, NYK 1610612752, OKC 1610612760, ORL 1610612753, PHI 1610612755, PHX 1610612756, POR 1610612757, SAC 1610612758, SAS 1610612759, TOR 1610612761, UTA 1610612762, WAS 1610612764, WSH 1610612764.

```python
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
```

`if __name__ == "__main__": fetch_and_store_teams()`.

- [ ] **Step 4: Re-run the test.** Expected: OK.

- [ ] **Step 5: Commit** `scrape_teams.py` and `tests/test_scrape_teams.py` with message `feat: seed NBA teams into SQLite`. Do not push.

---

### Task 3: Save schedule rows in SQLite

**Files:**
- Modify: `scrape_schedule.py`
- Test: `tests/test_scrape_schedule_store.py`

**Interfaces:**
- Consumes: `connect`, `upsert_team`, `upsert_match`
- Produces: `save_match(conn, team_map, match_data) -> int` where `team_map` maps abbreviation to team id.

- [ ] **Step 1: Write the failing test**

```python
import os
import tempfile
import unittest

os.environ["NBA_SQLITE_PATH"] = os.path.join(tempfile.mkdtemp(), "nba.sqlite")

import scrape_schedule
import sqlite_store


class ScheduleStoreTests(unittest.TestCase):
    def test_save_match_updates_same_pairing(self):
        conn = sqlite_store.connect(os.environ["NBA_SQLITE_PATH"])
        home = sqlite_store.upsert_team(conn, "LAL", "Lakers", "Los Angeles Lakers", None, 1)
        away = sqlite_store.upsert_team(conn, "BOS", "Celtics", "Boston Celtics", None, 2)
        team_map = {"LAL": home, "BOS": away}
        payload = {
            "date": "2026-10-18", "start_time": "2026-10-18T23:00:00Z",
            "home_abbr": "LAL", "away_abbr": "BOS", "status": "STATUS_SCHEDULED",
            "home_score": 0, "away_score": 0, "period_scores": None,
            "vegas_spread": -2.5, "vegas_total": 215.0,
        }
        first = scrape_schedule.save_match(conn, team_map, payload)
        payload["status"] = "STATUS_FINISHED"
        payload["home_score"] = 101
        second = scrape_schedule.save_match(conn, team_map, payload)
        self.assertEqual(first, second)
        status = conn.execute("SELECT status, home_score FROM matches WHERE id=?", (first,)).fetchone()
        self.assertEqual(status["status"], "STATUS_FINISHED")
        self.assertEqual(status["home_score"], 101)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it.** Expected: FAIL, `save_match` missing.

- [ ] **Step 3: Change `scrape_schedule.py`**

Add `import sqlite_store` and delete `from config import get_supabase_client`. `get_team_map(conn)` reads `SELECT id, code FROM teams` and keeps the existing `mapping_fix` loop. `scrape_schedule()` opens `sqlite_store.connect()` instead of Supabase. Replace the existing `existing = supabase... insert/update` block with `save_match(conn, team_map, payload)` where `payload` includes `home_abbr` and `away_abbr`. Keep the ESPN parsing, status names, and spread sign logic as they are.

```python
def save_match(conn, team_map, payload):
    row = dict(payload)
    row["home_team_id"] = team_map[row.pop("home_abbr")]
    row["away_team_id"] = team_map[row.pop("away_abbr")]
    return sqlite_store.upsert_match(conn, row)
```

- [ ] **Step 4: Re-run.** Expected: OK. Also run `python -m unittest tests.test_sqlite_store tests.test_scrape_teams tests.test_scrape_schedule_store -v`. Expected: all OK.

- [ ] **Step 5: Commit** with message `feat: write scraped games into SQLite`. Do not push.

---

### Task 4: Grade and predict against SQLite

**Files:**
- Modify: `grade_picks.py`
- Modify: `aggregate_picks.py`
- Test: `tests/test_grade_picks_store.py`

**Interfaces:**
- Consumes: `grade_pick`, `upsert_pick`, `connect`
- Produces: `grade_picks.settle(conn) -> int` and `aggregate_picks.upcoming_matches(conn, start_iso, end_iso) -> list[dict]`

`upcoming_matches` returns the same string comparison the Supabase query uses: `date >= start_iso AND date < end_iso`. Each match dict includes `home_team` and `away_team` with `code` and `nba_team_id`.

`settle` reproduces the current spread and total rules. Spread uses `line_info` and `recommended_team_id` against `home_score - away_score`. Total uses `ou_pick` against `vegas_total`. Only fill an outcome that is still null. Return the number of picks updated.

- [ ] **Step 1: Write the failing test**

```python
import os
import tempfile
import unittest

os.environ["NBA_SQLITE_PATH"] = os.path.join(tempfile.mkdtemp(), "nba.sqlite")

import grade_picks
import sqlite_store


class GradeTests(unittest.TestCase):
    def test_home_cover_and_under_total(self):
        conn = sqlite_store.connect(os.environ["NBA_SQLITE_PATH"])
        home = sqlite_store.upsert_team(conn, "LAL", "Lakers", "Los Angeles Lakers", None, 1)
        away = sqlite_store.upsert_team(conn, "BOS", "Celtics", "Boston Celtics", None, 2)
        match_id = sqlite_store.upsert_match(conn, {
            "date": "2026-10-18", "start_time": "2026-10-18T23:00:00Z",
            "home_team_id": home, "away_team_id": away, "status": "STATUS_FINISHED",
            "home_score": 110, "away_score": 100, "period_scores": None,
            "vegas_spread": -3.5, "vegas_total": 220.5,
        })
        sqlite_store.upsert_pick(conn, {
            "match_id": match_id, "recommended_team_id": home, "confidence_score": 60,
            "spread_logic": "en", "spread_logic_zh": "zh", "line_info": "-3.5",
            "ou_pick": "OVER", "ou_line": 220.5, "ou_confidence": 55,
            "analysis_content": "a", "analysis_content_zh": "甲",
            "predicted_margin": 4.0, "predicted_total": 230.0, "created_at": "2026-10-17T00:00:00",
        })
        updated = grade_picks.settle(conn)
        row = conn.execute("SELECT spread_outcome, total_outcome FROM aggregated_picks").fetchone()
        self.assertEqual(updated, 1)
        self.assertEqual(row["spread_outcome"], "WIN")
        self.assertEqual(row["total_outcome"], "LOSS")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it.** Expected: FAIL because `settle` does not exist.

- [ ] **Step 3: Implement `settle` and `upcoming_matches`**

Remove `get_supabase_client` from both files. `grade_picks()` calls `settle(sqlite_store.connect())`. `aggregate_picks.run()` loads matches from `upcoming_matches(conn, now.isoformat(), end_date.isoformat())` and writes each pick with `sqlite_store.upsert_pick`. Keep model loading, policy B, bilingual insight text, and `PREDICT_DAYS` unchanged. `h_id` and `a_id` come from `m["home_team"]["nba_team_id"]` and `m["away_team"]["nba_team_id"]`.

```python
def settle(conn):
    rows = conn.execute(
        """
        SELECT p.id AS pick_id, p.line_info, p.recommended_team_id, p.ou_pick,
               p.spread_outcome, p.total_outcome,
               m.home_team_id, m.home_score, m.away_score, m.vegas_total, m.status
        FROM aggregated_picks p
        JOIN matches m ON m.id = p.match_id
        WHERE m.status IN ('STATUS_FINAL', 'STATUS_FINISHED', 'Final')
        """
    ).fetchall()
    updated = 0
    for row in rows:
        spread = total = None
        if row["spread_outcome"] is None and row["line_info"] not in (None, ""):
            margin = row["home_score"] - row["away_score"]
            covered = margin + float(row["line_info"])
            if row["recommended_team_id"] == row["home_team_id"]:
                spread = "WIN" if covered > 0 else "LOSS" if covered < 0 else "PUSH"
            else:
                spread = "LOSS" if covered > 0 else "WIN" if covered < 0 else "PUSH"
        if row["total_outcome"] is None and row["ou_pick"] and row["vegas_total"] is not None:
            points = row["home_score"] + row["away_score"]
            line = float(row["vegas_total"])
            if points == line:
                total = "PUSH"
            elif row["ou_pick"] == "OVER":
                total = "WIN" if points > line else "LOSS"
            else:
                total = "WIN" if points < line else "LOSS"
        if spread is None and total is None:
            continue
        sqlite_store.grade_pick(conn, row["pick_id"], spread, total)
        updated += 1
    return updated


def upcoming_matches(conn, start_iso, end_iso):
    rows = conn.execute(
        """
        SELECT m.*, h.code AS home_code, h.nba_team_id AS home_nba,
               a.code AS away_code, a.nba_team_id AS away_nba
        FROM matches m
        JOIN teams h ON h.id = m.home_team_id
        JOIN teams a ON a.id = m.away_team_id
        WHERE m.date >= ? AND m.date < ?
        ORDER BY m.date
        """,
        (start_iso, end_iso),
    ).fetchall()
    matches = []
    for row in rows:
        item = dict(row)
        item["home_team"] = {"code": row["home_code"], "nba_team_id": row["home_nba"]}
        item["away_team"] = {"code": row["away_code"], "nba_team_id": row["away_nba"]}
        matches.append(item)
    return matches
```

- [ ] **Step 4: Re-run the new test and the previous unittest modules.** Expected: all OK.

- [ ] **Step 5: Commit** with message `feat: grade and predict from SQLite`. Do not push.

---

### Task 5: Export the public snapshot

**Files:**
- Create: `export_snapshot.py`
- Create: `web-app/data/public-snapshot.json`
- Test: `tests/test_export_snapshot.py`

**Interfaces:**
- Consumes: `export_snapshot(conn) -> dict` from `sqlite_store`
- Produces: `write_snapshot(conn, path: str) -> None` which writes pretty JSON ending in a newline.

- [ ] **Step 1: Write the failing test.** Seed one team, one match, and one pick in a temp database. Call `write_snapshot` to a temp file. Read it back and assert the three top-level keys and `matches[0].home_team.code`.

- [ ] **Step 2: Run it.** Expected: FAIL, module missing.

- [ ] **Step 3: Write `export_snapshot.py`**

```python
import json
import sqlite_store

SNAPSHOT_PATH = "web-app/data/public-snapshot.json"


def write_snapshot(conn, path=SNAPSHOT_PATH):
    payload = sqlite_store.export_snapshot(conn)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    write_snapshot(sqlite_store.connect())
```

Create `web-app/data/public-snapshot.json` as `{"teams":[],"matches":[],"picks":[]}` plus a trailing newline.

- [ ] **Step 4: Re-run the test.** Expected: OK.

- [ ] **Step 5: Commit** `export_snapshot.py`, `tests/test_export_snapshot.py`, and `web-app/data/public-snapshot.json` with message `feat: export the public JSON snapshot`. Do not push.

---

### Task 6: Mount check and script order

**Files:**
- Modify: `scripts/pi_update.sh`
- Modify: `scripts/test_pi_update.sh`

**Interfaces:**
- Consumes: the Python entry points `scrape_teams.py`, `scrape_schedule.py`, `grade_picks.py`, `aggregate_picks.py`, `export_snapshot.py`
- Produces: `main` exits 1 with stdout `sqlite mount missing` when `/mnt/sports-db` is not a mount or not writable, before any Python. Tests set `PI_UPDATE_MOUNT_CHECK=skip` so the sandbox is not required to be a mount point.

- [ ] **Step 1: Update the bash expectations** in `make_sandbox` to `export PI_UPDATE_MOUNT_CHECK=skip`. Change the light-run call list to `scrape_teams.py,scrape_schedule.py,grade_picks.py,aggregate_picks.py,export_snapshot.py`. Change the retrain call list to insert `scrape_teams.py` first and `export_snapshot.py` last, with the four training scripts still between `grade_picks.py` and `aggregate_picks.py`. Add this case after the lock test:

```bash
SANDBOX=$(mktemp -d)
export PI_UPDATE_ROOT="$SANDBOX"
export PI_UPDATE_PYTHON="$SANDBOX/bin/python"
export PI_UPDATE_MOUNT_CHECK=mountpoint
export PI_UPDATE_MOUNT="$SANDBOX/not-a-mount"
mkdir -p "$PI_UPDATE_MOUNT"
set +e
( main > "$SANDBOX/mount-out.txt" )
rc=$?
set -e
if [ "$rc" -eq 0 ] || ! grep -qx "sqlite mount missing" "$SANDBOX/mount-out.txt"; then
  echo "FAIL mount check"
  exit 1
fi
echo "PASS mount check"
```

- [ ] **Step 2: Run the bash test on the Pi.** Expected: FAIL on the new call order or the missing mount message.

```powershell
scp "D:\sports-predictor\.worktrees\pi-cron-pipeline\scripts\pi_update.sh" "D:\sports-predictor\.worktrees\pi-cron-pipeline\scripts\test_pi_update.sh" tedliu@192.168.0.101:/tmp/sports-predictor-tests/
ssh tedliu@192.168.0.101 "sed -i 's/\r$//' /tmp/sports-predictor-tests/*.sh && env -u TMPDIR bash /tmp/sports-predictor-tests/test_pi_update.sh"
```

- [ ] **Step 3: Update `main` in `scripts/pi_update.sh`**

After the lock is acquired and before `echo "抓賽程"`:

```bash
  mount_dir="${PI_UPDATE_MOUNT:-/mnt/sports-db}"
  mount_check="${PI_UPDATE_MOUNT_CHECK:-mountpoint}"
  if [ "$mount_check" != "skip" ]; then
    if ! mountpoint -q "$mount_dir" || [ ! -w "$mount_dir" ]; then
      echo "sqlite mount missing"
      exit 1
    fi
  fi
```

Replace the scrape line with:

```bash
  echo "抓賽程"
  "$py" scrape_teams.py
  "$py" scrape_schedule.py
```

After `aggregate_picks.py` and before `rm -f data/PlayerStatistics.csv`:

```bash
  "$py" export_snapshot.py
```

- [ ] **Step 4: Re-run the Pi bash test.** Expected: `ALL PASS`, including `PASS mount check`.

- [ ] **Step 5: Commit** both scripts with message `feat: export the snapshot from the Pi update script`. Do not push.

---

### Task 7: Read the snapshot in the site

**Files:**
- Create: `web-app/lib/snapshot.mjs`
- Create: `web-app/lib/snapshot.test.mjs`
- Modify: `web-app/app/page.tsx`
- Modify: `web-app/app/match/[id]/page.tsx`
- Delete: `web-app/lib/supabase.ts`

**Interfaces:**
- Consumes: the snapshot JSON shape from Task 5
- Produces:
  - `loadSnapshot()` fetches `process.env.SNAPSHOT_URL` or the raw GitHub URL with `cache: 'no-store'`. On any failure it returns `{teams:[], matches:[], picks:[]}`.
  - `matchesOnDate(snapshot, yyyyMmDd)` keeps matches whose `start_time` is in `[yyyy-mm-ddT11:00:00.000Z, +24h)`.
  - `latestDate(snapshot, today)` returns the earliest `matches.date` greater than or equal to `today`, otherwise the latest date before `today`, otherwise null.
  - `pickForMatch(snapshot, matchId)` returns the pick whose `match_id` equals `Number(matchId)`, or null.
  - `historyPicks(snapshot)` returns picks with `spread_outcome` or `total_outcome` not null, ordered by `matches.date` ascending. Each item is `{spread_outcome, total_outcome, matches: {date}}`.

- [ ] **Step 1: Write `web-app/lib/snapshot.test.mjs`**

```javascript
import assert from "node:assert/strict";
import { latestDate, matchesOnDate, pickForMatch, historyPicks, loadSnapshot } from "./snapshot.mjs";

const snapshot = {
  teams: [],
  matches: [
    { id: 1, date: "2026-10-17", start_time: "2026-10-17T23:00:00Z", home_team: { code: "LAL" }, away_team: { code: "BOS" } },
    { id: 2, date: "2026-10-18", start_time: "2026-10-18T23:00:00Z", home_team: { code: "NYK" }, away_team: { code: "MIA" } },
  ],
  picks: [
    { match_id: 1, spread_outcome: "WIN", total_outcome: null, matches: { date: "2026-10-17" } },
    { match_id: 2, spread_outcome: null, total_outcome: null, matches: { date: "2026-10-18" } },
  ],
};

assert.equal(latestDate(snapshot, "2026-10-18"), "2026-10-18");
assert.equal(latestDate(snapshot, "2026-10-19"), "2026-10-18");
assert.deepEqual(matchesOnDate(snapshot, "2026-10-17").map((m) => m.id), [1]);
assert.equal(pickForMatch(snapshot, "1").match_id, 1);
assert.equal(pickForMatch(snapshot, "9"), null);
assert.deepEqual(historyPicks(snapshot).map((p) => p.match_id), [1]);
assert.equal(typeof loadSnapshot, "function");
console.log("PASS snapshot");
```

- [ ] **Step 2: Run `node web-app/lib/snapshot.test.mjs`.** Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement `snapshot.mjs` and switch the two pages.**

`page.tsx` drops the Supabase import. It `await loadSnapshot()`, redirects with `latestDate` when `params.date` is missing, filters with `matchesOnDate`, and builds `picks` the same way it does now: each match spread with its pick, plus `matches: match`. `historyPicks(snapshot)` replaces `allHistoryData`. A failed load therefore renders the current empty board.

`match/[id]/page.tsx` uses `pickForMatch`. Null returns `notFound()`. Pass that pick to `MatchDetailView` unchanged.

Delete `web-app/lib/supabase.ts`. Do not edit `HomeMarketBoard`, `StatsDashboard`, or `MatchDetailView`.

- [ ] **Step 4: Re-run `node web-app/lib/snapshot.test.mjs`.** Expected: all assertions pass and the process exits 0. Search the web app for `supabase` and expect no matches.

```powershell
rg -n "supabase" web-app
```

- [ ] **Step 5: Commit** with message `feat: read the public snapshot instead of Supabase`. Do not push.

---

### Task 8: Create the image, push, and prove a run

**Files:**
- No further repo files unless the manual run commits a snapshot by itself.

**Interfaces:**
- Consumes: `scripts/pi_update.sh` and `sqlite_store.py` from the earlier tasks, on `origin/main` after the push.

- [ ] **Step 1: Push the branch onto main and update the Pi checkout**

```powershell
git -C "D:\sports-predictor\.worktrees\pi-cron-pipeline" push origin HEAD:main
ssh tedliu@192.168.0.101 "git -C /home/tedliu/sports-predictor pull --ff-only origin main"
```

Expected: fast-forward, no force push.

- [ ] **Step 2: Create the image once**

```powershell
ssh tedliu@192.168.0.101 "if [ ! -f /mnt/usb/sports-predictor/nba.img ]; then sudo mkdir -p /mnt/usb/sports-predictor /mnt/sports-db && sudo fallocate -l 2G /mnt/usb/sports-predictor/nba.img && sudo mkfs.ext4 -F /mnt/usb/sports-predictor/nba.img; fi; grep -qx '/mnt/usb/sports-predictor/nba.img /mnt/sports-db ext4 loop,defaults 0 0' /etc/fstab || echo '/mnt/usb/sports-predictor/nba.img /mnt/sports-db ext4 loop,defaults 0 0' | sudo tee -a /etc/fstab; sudo mount /mnt/sports-db && sudo chown tedliu:tedliu /mnt/sports-db && touch /mnt/sports-db/nba.sqlite && mountpoint -q /mnt/sports-db && echo PASS mount"
```

Expected: `PASS mount`. If `nba.img` already exists, the command must not run `mkfs`.

- [ ] **Step 3: Manual run outside 22:00–22:29 Taipei**

```powershell
ssh tedliu@192.168.0.101 "TZ=Asia/Taipei date +%H:%M; /home/tedliu/sports-predictor/scripts/pi_update.sh >> /home/tedliu/sports-predictor/logs/pi_update.log 2>&1; echo EXIT:`$?; tail -n 50 /home/tedliu/sports-predictor/logs/pi_update.log"
```

Expected: `EXIT:0`, and the log contains `抓賽程`, `結算`, `跳過重訓`, and `預測`.

```powershell
ssh tedliu@192.168.0.101 "/home/tedliu/sports-predictor/.venv/bin/python -c \"import sqlite3; c=sqlite3.connect('/mnt/sports-db/nba.sqlite'); print('teams', c.execute('select count(*) from teams').fetchone()[0]); print('matches', c.execute('select count(*) from matches').fetchone()[0])\""
```

Expected: `teams 30` and `matches` greater than 0.

- [ ] **Step 4: Confirm the snapshot and the crontab**

If the run committed, `git -C /home/tedliu/sports-predictor log -1 --format=%s` is `🤖 Auto-update: Schedule, Odds, Picks & CSV Data` and `git status` does not show a force. `web-app/data/public-snapshot.json` on `main` contains a `teams` array of 30 objects.

`crontab -l` still contains the SSD cleanup line, both HSR schedule lines, and exactly one `pi_update.sh` line.

- [ ] **Step 5: Run the store tests and the bash tests once more**

```powershell
python -m unittest discover -s tests -v
ssh tedliu@192.168.0.101 "sed -i 's/\r$//' /home/tedliu/sports-predictor/scripts/*.sh && env -u TMPDIR bash /home/tedliu/sports-predictor/scripts/test_pi_update.sh"
```

Expected: unittest OK, bash `ALL PASS`.
