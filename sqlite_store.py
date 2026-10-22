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
  analysis_facts TEXT,
  predicted_margin REAL,
  predicted_total REAL,
  spread_outcome TEXT,
  total_outcome TEXT,
  created_at TEXT
);
"""

# Columns added after the first deploy; connect() adds them to older databases.
PICK_MIGRATIONS = (("analysis_facts", "TEXT"),)

PICK_FIELDS = (
    "recommended_team_id", "confidence_score", "spread_logic", "spread_logic_zh",
    "line_info", "ou_pick", "ou_line", "ou_confidence", "analysis_content",
    "analysis_content_zh", "analysis_facts", "predicted_margin", "predicted_total", "created_at",
)


def connect(path=None):
    db_path = path or os.environ.get("NBA_SQLITE_PATH", DEFAULT_PATH)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(aggregated_picks)")}
    for column, col_type in PICK_MIGRATIONS:
        if column not in existing:
            conn.execute(f"ALTER TABLE aggregated_picks ADD COLUMN {column} {col_type}")
    conn.commit()
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
    fields = {
        "start_time": row.get("start_time"),
        "status": row.get("status"),
        "home_score": row.get("home_score"),
        "away_score": row.get("away_score"),
        "period_scores": periods_text,
    }
    # Absent odds keys keep the line already stored. A score refresh must not wipe it.
    if "vegas_spread" in row:
        fields["vegas_spread"] = row.get("vegas_spread")
    if "vegas_total" in row:
        fields["vegas_total"] = row.get("vegas_total")
    existing = conn.execute(
        "SELECT id FROM matches WHERE date=? AND home_team_id=? AND away_team_id=?",
        (row["date"], row["home_team_id"], row["away_team_id"]),
    ).fetchone()
    if existing:
        assignments = ", ".join(f"{name}=?" for name in fields)
        conn.execute(
            f"UPDATE matches SET {assignments} WHERE id=?",
            tuple(fields.values()) + (existing["id"],),
        )
        match_id = existing["id"]
    else:
        columns = list(fields) + ["date", "home_team_id", "away_team_id"]
        values = list(fields.values()) + [row["date"], row["home_team_id"], row["away_team_id"]]
        placeholders = ", ".join("?" for _ in columns)
        cur = conn.execute(
            f"INSERT INTO matches ({', '.join(columns)}) VALUES ({placeholders})",
            values,
        )
        match_id = cur.lastrowid
    conn.commit()
    return match_id


def upsert_pick(conn, row):
    facts = row.get("analysis_facts")
    if facts is not None and not isinstance(facts, str):
        row = dict(row)
        row["analysis_facts"] = json.dumps(facts, ensure_ascii=False, default=str)
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
        facts = pick.get("analysis_facts")
        if isinstance(facts, str) and facts:
            try:
                pick["analysis_facts"] = json.loads(facts)
            except ValueError:
                pick["analysis_facts"] = None
        match = conn.execute("SELECT * FROM matches WHERE id=?", (pick["match_id"],)).fetchone()
        pick["matches"] = _match_public(conn, match) if match else None
        rec = _team(conn, pick["recommended_team_id"])
        pick["recommended_team"] = {"code": rec["code"], "logo_url": rec["logo_url"]} if rec else None
        picks.append(pick)
    return {"teams": teams, "matches": matches, "picks": picks}
