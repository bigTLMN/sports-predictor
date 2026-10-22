"""Research-style match write-ups from the numbers the picker already has.

Everything here is derived from data on hand: this season's results in SQLite,
the box-score profile in TeamStatistics.csv, the posted lines, and the model's
own projection. No external calls. Output is a bilingual text (section headers
start with "## ", bullets with "• ") plus a facts dict the detail page renders
as a comparison table.
"""
from __future__ import annotations

import math
import random
from datetime import date as date_type
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

FINISHED = ("STATUS_FINISHED", "STATUS_FINAL", "Final")
PROFILE_GAMES = 10
# Standard deviation of NBA outcomes around the closing line. Used only when this
# season does not yet have enough graded games with lines to measure its own.
DEFAULT_SIGMA_SPREAD = 12.5
DEFAULT_SIGMA_TOTAL = 19.0
MIN_GAMES_FOR_SIGMA = 40
EFFECT_YEARS = 3

LOG_COLS = [
    "gameDateTimeEst", "teamId", "opponentTeamId", "home", "win", "teamScore", "opponentScore", "gameType",
    "fieldGoalsPercentage", "threePointersAttempted", "threePointersPercentage",
    "freeThrowsPercentage", "reboundsTotal", "reboundsOffensive", "assists", "steals",
    "blocks", "turnovers", "plusMinusPoints", "pointsInThePaint", "pointsFastBreak",
    "pointsFromTurnovers", "pointsSecondChance", "benchPoints",
]

# key, column, English label, Chinese label, better direction, scale for ranking, format
STAT_ROWS = [
    ("ppg", "teamScore", "Points", "得分", "high", 6.0, "num"),
    ("papg", "opponentScore", "Points allowed", "失分", "low", 6.0, "num"),
    ("net", "plusMinusPoints", "Net margin", "淨勝分", "high", 6.0, "signed"),
    ("fg", "fieldGoalsPercentage", "FG%", "命中率", "high", 0.03, "pct"),
    ("tp", "threePointersPercentage", "3P%", "三分命中率", "high", 0.04, "pct"),
    ("tpa", "threePointersAttempted", "3PA", "三分出手", None, 5.0, "num"),
    ("ft", "freeThrowsPercentage", "FT%", "罰球命中率", "high", 0.05, "pct"),
    ("reb", "reboundsTotal", "Rebounds", "籃板", "high", 4.0, "num"),
    ("oreb", "reboundsOffensive", "Off. rebounds", "進攻籃板", "high", 2.5, "num"),
    ("ast", "assists", "Assists", "助攻", "high", 3.0, "num"),
    ("tov", "turnovers", "Turnovers", "失誤", "low", 2.0, "num"),
    ("paint", "pointsInThePaint", "Paint points", "禁區得分", "high", 6.0, "num"),
    ("fb", "pointsFastBreak", "Fast-break points", "快攻得分", "high", 4.0, "num"),
    ("pot", "pointsFromTurnovers", "Points off turnovers", "失誤轉換得分", "high", 4.0, "num"),
    ("bench", "benchPoints", "Bench points", "板凳得分", "high", 6.0, "num"),
]

NARRATIVE_EN = {
    "ppg": "scores {rec} a night to {opp}", "papg": "gives up {rec} to {opp}",
    "net": "outscores opponents by {rec} per game against {opp}", "fg": "shoots {rec} from the floor to {opp}",
    "tp": "hits {rec} from three against {opp}", "ft": "converts {rec} at the line to {opp}",
    "reb": "pulls {rec} rebounds to {opp}", "oreb": "grabs {rec} offensive boards to {opp}",
    "ast": "records {rec} assists to {opp}", "tov": "commits {rec} turnovers to {opp}",
    "paint": "produces {rec} paint points to {opp}", "fb": "runs for {rec} fast-break points to {opp}",
    "pot": "turns mistakes into {rec} points to {opp}", "bench": "gets {rec} from the bench to {opp}",
    "tpa": "launches {rec} threes to {opp}",
}
NARRATIVE_ZH = {
    "ppg": "場均得 {rec} 分，對手 {opp}", "papg": "場均失 {rec} 分，對手 {opp}",
    "net": "場均淨勝 {rec} 分，對手 {opp}", "fg": "命中率 {rec}，對手 {opp}",
    "tp": "三分命中 {rec}，對手 {opp}", "ft": "罰球 {rec}，對手 {opp}",
    "reb": "場均 {rec} 籃板，對手 {opp}", "oreb": "進攻籃板 {rec} 個，對手 {opp}",
    "ast": "助攻 {rec} 次，對手 {opp}", "tov": "失誤 {rec} 次，對手 {opp}",
    "paint": "禁區拿 {rec} 分，對手 {opp}", "fb": "快攻 {rec} 分，對手 {opp}",
    "pot": "失誤轉換得 {rec} 分，對手 {opp}", "bench": "板凳貢獻 {rec} 分，對手 {opp}",
    "tpa": "三分出手 {rec} 次，對手 {opp}",
}


# ---------------------------------------------------------------- formatting

def _f(value, fmt: str) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "—"
    if fmt == "pct":
        return f"{value * 100:.1f}%"
    if fmt == "signed":
        return f"{value:+.1f}"
    return f"{value:.1f}"


def _signed(value: float) -> str:
    return f"{value:+.1f}"


def _line(value: float) -> str:
    if abs(value) < 1e-6:
        return "PK"
    return f"{value:+.1f}"


def _pct(p: float) -> str:
    return f"{p * 100:.0f}%"


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


# ---------------------------------------------------------------- data loads

def load_team_logs(csv_path: str = "data/TeamStatistics.csv") -> pd.DataFrame:
    df = pd.read_csv(csv_path, usecols=lambda c: c in LOG_COLS, low_memory=False)
    df["gameDateTimeEst"] = pd.to_datetime(
        df["gameDateTimeEst"].astype(str).str.slice(0, 10), errors="coerce"
    )
    df = df.dropna(subset=["gameDateTimeEst", "teamId"])
    df["teamId"] = df["teamId"].astype(int)
    if "opponentTeamId" in df.columns:
        df["opponentTeamId"] = pd.to_numeric(df["opponentTeamId"], errors="coerce")
    return df.sort_values(["teamId", "gameDateTimeEst"])


NBA_TEAM_ID_MIN, NBA_TEAM_ID_MAX = 1610612737, 1610612766
GAME_TYPES = ("Regular Season", "Playoffs", "Play-in Tournament", "Emirates NBA Cup")


def _nba_only(logs: pd.DataFrame) -> pd.DataFrame:
    """Current franchises and real games only (no All-Star or exhibition rows)."""
    mask = (logs["teamId"] >= NBA_TEAM_ID_MIN) & (logs["teamId"] <= NBA_TEAM_ID_MAX)
    if "gameType" in logs.columns:
        mask &= logs["gameType"].isin(GAME_TYPES) | logs["gameType"].isna()
    return logs[mask]


def team_profile(logs: pd.DataFrame, nba_team_id: int, games: int = PROFILE_GAMES) -> Optional[dict]:
    if logs is None or logs.empty:
        return None
    sub = _nba_only(logs[logs["teamId"] == int(nba_team_id)]).tail(games)
    if sub.empty:
        return None
    out = {"games": int(len(sub)), "last_date": sub["gameDateTimeEst"].max().date()}
    for key, col, *_ in STAT_ROWS:
        out[key] = float(pd.to_numeric(sub[col], errors="coerce").mean()) if col in sub.columns else None
    if "win" in sub.columns:
        wins = pd.to_numeric(sub["win"], errors="coerce").fillna(0)
        out["win_rate"] = float(wins.mean())
    margins = pd.to_numeric(sub["teamScore"], errors="coerce") - pd.to_numeric(sub["opponentScore"], errors="coerce")
    out["margin_sd"] = float(margins.std(ddof=0)) if len(margins) > 1 else None
    return out


def league_context(logs: pd.DataFrame, games: int = PROFILE_GAMES) -> dict:
    """League averages and per-team ranks over each team's last `games` box scores."""
    if logs is None or logs.empty:
        return {"teams": 0, "avg": {}, "rank": {}}
    logs = _nba_only(logs)
    profiles = {}
    for team_id in logs["teamId"].unique():
        prof = team_profile(logs, int(team_id), games)
        if prof and prof["games"] >= 3:
            profiles[int(team_id)] = prof
    avg, rank = {}, {tid: {} for tid in profiles}
    for key, _col, _en, _zh, better, _scale, _fmt in STAT_ROWS:
        values = [(tid, p[key]) for tid, p in profiles.items() if p.get(key) is not None and not np.isnan(p[key])]
        if not values:
            continue
        avg[key] = float(np.mean([v for _, v in values]))
        reverse = better != "low"
        ordered = sorted(values, key=lambda t: t[1], reverse=reverse)
        for position, (tid, _v) in enumerate(ordered, start=1):
            rank[tid][key] = position
    return {"teams": len(profiles), "avg": avg, "rank": rank}


def historical_effects(logs: pd.DataFrame, years: int = EFFECT_YEARS) -> dict:
    """Home-court and back-to-back effects measured from the box-score history."""
    out = {}
    if logs is None or logs.empty:
        return out
    df = _nba_only(logs)
    cutoff = df["gameDateTimeEst"].max() - pd.Timedelta(days=365 * years)
    df = df[df["gameDateTimeEst"] >= cutoff].copy()
    if df.empty:
        return out
    df["margin"] = pd.to_numeric(df["teamScore"], errors="coerce") - pd.to_numeric(df["opponentScore"], errors="coerce")
    df = df.dropna(subset=["margin"])
    out["since"] = cutoff.date().isoformat()
    out["years"] = years
    home = df[pd.to_numeric(df["home"], errors="coerce") == 1]
    if len(home):
        out["home_margin"] = float(home["margin"].mean())
        out["home_win_rate"] = float((home["margin"] > 0).mean())
        out["home_n"] = int(len(home))
        out["avg_total"] = float((pd.to_numeric(home["teamScore"]) + pd.to_numeric(home["opponentScore"])).mean())
    df = df.sort_values(["teamId", "gameDateTimeEst"])
    gap = df.groupby("teamId")["gameDateTimeEst"].diff().dt.days
    b2b = df[gap <= 1]
    if len(b2b):
        out["b2b_margin"] = float(b2b["margin"].mean())
        out["b2b_win_rate"] = float((b2b["margin"] > 0).mean())
        out["b2b_n"] = int(len(b2b))
    return out


def season_ranks(conn, before_date: str) -> dict:
    """This season's per-team ppg / papg / margin with ranks, from the SQLite results."""
    rows = conn.execute(
        """
        SELECT home_team_id, away_team_id, home_score, away_score, status
        FROM matches WHERE date < ? AND status IN ('STATUS_FINAL', 'STATUS_FINISHED', 'Final')
        """,
        (before_date,),
    ).fetchall()
    pf, pa = {}, {}
    for r in rows:
        if r["home_score"] is None or r["away_score"] is None or (r["home_score"] == 0 and r["away_score"] == 0):
            continue
        pf.setdefault(r["home_team_id"], []).append(r["home_score"])
        pa.setdefault(r["home_team_id"], []).append(r["away_score"])
        pf.setdefault(r["away_team_id"], []).append(r["away_score"])
        pa.setdefault(r["away_team_id"], []).append(r["home_score"])
    teams = {tid: {"ppg": float(np.mean(pf[tid])), "papg": float(np.mean(pa[tid]))} for tid in pf}
    for tid in teams:
        teams[tid]["margin"] = teams[tid]["ppg"] - teams[tid]["papg"]
    ranks = {tid: {} for tid in teams}
    for key, reverse in (("ppg", True), ("papg", False), ("margin", True)):
        ordered = sorted(teams, key=lambda t: teams[t][key], reverse=reverse)
        for position, tid in enumerate(ordered, start=1):
            ranks[tid][key] = position
    return {"teams": len(teams), "values": teams, "rank": ranks}


def model_record(conn, before_date: str) -> dict:
    """Graded results of this season's published picks, overall and by confidence."""
    rows = conn.execute(
        """
        SELECT p.confidence_score, p.ou_confidence, p.spread_outcome, p.total_outcome, p.line_info
        FROM aggregated_picks p JOIN matches m ON m.id = p.match_id
        WHERE m.date < ?
        """,
        (before_date,),
    ).fetchall()
    spread = [(r["confidence_score"], r["spread_outcome"]) for r in rows if r["spread_outcome"] in ("WIN", "LOSS") and r["line_info"] not in (None, "")]
    total = [(r["ou_confidence"], r["total_outcome"]) for r in rows if r["total_outcome"] in ("WIN", "LOSS")]

    def tally(items, min_conf=None):
        picked = [o for c, o in items if min_conf is None or (c is not None and c >= min_conf)]
        return {"w": sum(1 for o in picked if o == "WIN"), "l": sum(1 for o in picked if o == "LOSS")}

    return {"spread": tally(spread), "total": tally(total), "_spread": spread, "_total": total, "tally": tally}


def line_sigmas(conn, before_date: str) -> dict:
    """Std dev of outcomes vs the posted lines this season, or defaults while the sample is small."""
    rows = conn.execute(
        """
        SELECT home_score, away_score, vegas_spread, vegas_total FROM matches
        WHERE date < ? AND status IN ('STATUS_FINAL', 'STATUS_FINISHED', 'Final')
          AND home_score IS NOT NULL AND away_score IS NOT NULL
        """,
        (before_date,),
    ).fetchall()
    spread_res = [(r["home_score"] - r["away_score"]) + float(r["vegas_spread"]) for r in rows if r["vegas_spread"] is not None]
    total_res = [(r["home_score"] + r["away_score"]) - float(r["vegas_total"]) for r in rows if r["vegas_total"] is not None]
    out = {"spread": DEFAULT_SIGMA_SPREAD, "total": DEFAULT_SIGMA_TOTAL, "spread_n": len(spread_res), "total_n": len(total_res), "measured": False}
    if len(spread_res) >= MIN_GAMES_FOR_SIGMA:
        out["spread"] = float(min(16.0, max(10.0, np.std(spread_res))))
        out["measured"] = True
    if len(total_res) >= MIN_GAMES_FOR_SIGMA:
        out["total"] = float(min(24.0, max(15.0, np.std(total_res))))
    return out


def head_to_head(logs: pd.DataFrame, rec_nba: int, opp_nba: int, games: int = 3) -> List[dict]:
    if logs is None or logs.empty or "opponentTeamId" not in logs.columns:
        return []
    sub = logs[(logs["teamId"] == int(rec_nba)) & (logs["opponentTeamId"] == int(opp_nba))].tail(games)
    rows = []
    for _, r in sub.iterrows():
        rows.append({
            "date": r["gameDateTimeEst"].date().isoformat(),
            "won": bool(int(r.get("win", 0) or 0)),
            "for": int(r["teamScore"]), "against": int(r["opponentScore"]),
        })
    return rows


def season_form(conn, team_db_id: int, before_date: str) -> dict:
    rows = conn.execute(
        """
        SELECT m.date, m.home_team_id, m.away_team_id, m.home_score, m.away_score,
               m.vegas_spread, m.vegas_total, m.status,
               h.code AS home_code, a.code AS away_code
        FROM matches m
        JOIN teams h ON h.id = m.home_team_id
        JOIN teams a ON a.id = m.away_team_id
        WHERE (m.home_team_id = ? OR m.away_team_id = ?) AND m.date < ?
        ORDER BY m.date
        """,
        (team_db_id, team_db_id, before_date),
    ).fetchall()
    games = []
    for r in rows:
        if r["status"] not in FINISHED or r["home_score"] is None or r["away_score"] is None:
            continue
        is_home = r["home_team_id"] == team_db_id
        pf = r["home_score"] if is_home else r["away_score"]
        pa = r["away_score"] if is_home else r["home_score"]
        if pf == 0 and pa == 0:
            continue
        spread = r["vegas_spread"]
        cover = None
        if spread is not None:
            edge = (pf - pa) + float(spread) if is_home else (pf - pa) - float(spread)
            cover = "W" if edge > 0 else ("L" if edge < 0 else "P")
        total_result = None
        if r["vegas_total"] is not None:
            points = pf + pa
            total_result = "O" if points > float(r["vegas_total"]) else ("U" if points < float(r["vegas_total"]) else "P")
        games.append({
            "date": r["date"], "home": is_home, "won": pf > pa, "pf": pf, "pa": pa,
            "opp": r["away_code"] if is_home else r["home_code"], "ats": cover, "ou": total_result,
        })
    form = {"games": len(games)}
    if not games:
        return form
    form["wins"] = sum(1 for g in games if g["won"])
    form["losses"] = len(games) - form["wins"]
    form["home_record"] = (sum(1 for g in games if g["home"] and g["won"]), sum(1 for g in games if g["home"] and not g["won"]))
    form["away_record"] = (sum(1 for g in games if not g["home"] and g["won"]), sum(1 for g in games if not g["home"] and not g["won"]))
    form["ppg"] = sum(g["pf"] for g in games) / len(games)
    form["papg"] = sum(g["pa"] for g in games) / len(games)
    form["margin"] = form["ppg"] - form["papg"]
    ats = [g["ats"] for g in games if g["ats"]]
    form["ats"] = (ats.count("W"), ats.count("L"), ats.count("P")) if ats else None
    ou = [g["ou"] for g in games if g["ou"]]
    form["ou"] = (ou.count("O"), ou.count("U"), ou.count("P")) if ou else None
    streak_char = "W" if games[-1]["won"] else "L"
    streak = 0
    for g in reversed(games):
        if g["won"] == games[-1]["won"]:
            streak += 1
        else:
            break
    form["streak"] = f"{streak_char}{streak}"
    form["last"] = games[-3:]
    form["last_date"] = games[-1]["date"]
    return form


def rest_days(form: dict, match_date: str) -> Optional[int]:
    last = form.get("last_date")
    if not last:
        return None
    try:
        gap = (date_type.fromisoformat(match_date[:10]) - date_type.fromisoformat(last[:10])).days
    except ValueError:
        return None
    return gap if 0 <= gap <= 20 else None


# ---------------------------------------------------------------- edges

def ranked_edges(rec: Optional[dict], opp: Optional[dict]) -> Tuple[list, list]:
    """Return (rec_edges, opp_edges) as lists of (key, z, rec_val, opp_val) sorted by size."""
    if not rec or not opp:
        return [], []
    plus, minus = [], []
    for key, _col, _en, _zh, better, scale, _fmt in STAT_ROWS:
        if better is None:
            continue
        rv, ov = rec.get(key), opp.get(key)
        if rv is None or ov is None or np.isnan(rv) or np.isnan(ov):
            continue
        z = (rv - ov) / scale
        if better == "low":
            z = -z
        if z >= 0.35:
            plus.append((key, z, rv, ov))
        elif z <= -0.35:
            minus.append((key, -z, rv, ov))
    plus.sort(key=lambda t: t[1], reverse=True)
    minus.sort(key=lambda t: t[1], reverse=True)
    return plus, minus


def _stat_meta(key: str):
    for row in STAT_ROWS:
        if row[0] == key:
            return row
    raise KeyError(key)


# ---------------------------------------------------------------- writer

def _conf_word(conf: float, zh: bool) -> str:
    if conf >= 78:
        return "高" if zh else "high"
    if conf >= 64:
        return "中等" if zh else "moderate"
    return "偏低" if zh else "modest"


def _record(form: dict) -> str:
    return f"{form.get('wins', 0)}-{form.get('losses', 0)}"


def _last_results_en(form: dict) -> str:
    parts = []
    for g in form.get("last", []):
        where = "vs" if g["home"] else "at"
        parts.append(f"{'W' if g['won'] else 'L'} {g['pf']}-{g['pa']} {where} {g['opp']}")
    return ", ".join(parts)


def _last_results_zh(form: dict) -> str:
    parts = []
    for g in form.get("last", []):
        where = "主場" if g["home"] else "客場"
        parts.append(f"{where}{'勝' if g['won'] else '負'} {g['opp']} {g['pf']}-{g['pa']}")
    return "、".join(parts)


def _rank_note_en(rank: Optional[int], n: int) -> str:
    return f" ({_ordinal(rank)} of {n})" if rank and n else ""


def _rank_note_zh(rank: Optional[int], n: int) -> str:
    return f"（{n} 隊中第 {rank}）" if rank and n else ""


def quantify(ctx: dict) -> dict:
    """Probabilities and league-relative numbers the write-up and the facts panel both use."""
    league = ctx.get("league") or {}
    sig = league.get("sigmas") or {}
    sigma_s = float(sig.get("spread", DEFAULT_SIGMA_SPREAD))
    sigma_t = float(sig.get("total", DEFAULT_SIGMA_TOTAL))
    rec_home = bool(ctx["rec_is_home"])
    spread_home = ctx.get("vegas_spread")
    rec_line = None if spread_home is None else (float(spread_home) if rec_home else -float(spread_home))
    model_rec = float(ctx["pred_margin_rec"])
    market_rec = -rec_line if rec_line is not None else 0.0
    edge = model_rec - market_rec
    total_line = ctx.get("vegas_total")
    pred_total = float(ctx["pred_total"])
    q = {
        "sigma_spread": round(sigma_s, 1), "sigma_total": round(sigma_t, 1),
        "sigma_measured": bool(sig.get("measured")), "sigma_n": int(sig.get("spread_n") or 0),
        "p_cover": norm_cdf(edge / sigma_s),
        "p_win_model": norm_cdf(model_rec / sigma_s),
        "p_win_market": norm_cdf(market_rec / sigma_s) if rec_line is not None else None,
        "p_total": None,
    }
    if total_line is not None:
        diff = pred_total - float(total_line)
        q["p_total"] = norm_cdf(abs(diff) / sigma_t)  # probability of the side the model picked
    return q


def build_insight(ctx: dict) -> Tuple[str, str, dict]:
    """ctx keys: see aggregate_picks.run(). Returns (en, zh, facts)."""
    rec, opp = ctx["rec_code"], ctx["opp_code"]
    rec_name = ctx.get("rec_name") or rec
    opp_name = ctx.get("opp_name") or opp
    rec_home = bool(ctx["rec_is_home"])
    rng = random.Random(f"{ctx.get('match_id')}:{ctx.get('date')}:{rec}:{opp}")

    spread_home = ctx.get("vegas_spread")
    has_spread = spread_home is not None and abs(float(spread_home)) > 1e-6
    rec_line = None
    if spread_home is not None:
        rec_line = float(spread_home) if rec_home else -float(spread_home)
    model_rec = float(ctx["pred_margin_rec"])
    raw_rec = float(ctx.get("raw_margin_rec", model_rec))
    market_rec = -rec_line if rec_line is not None else 0.0
    edge_pts = model_rec - market_rec

    total_line = ctx.get("vegas_total")
    total_default = bool(ctx.get("total_is_default"))
    pred_total = float(ctx["pred_total"])
    ou = ctx["ou_pick"]
    total_edge = pred_total - float(total_line) if total_line is not None else 0.0

    conf = float(ctx["confidence"])
    ou_conf = float(ctx["ou_confidence"])
    withheld = bool(ctx.get("withhold_spread"))

    rec_form, opp_form = ctx.get("rec_form") or {}, ctx.get("opp_form") or {}
    rec_prof, opp_prof = ctx.get("rec_profile"), ctx.get("opp_profile")
    rec_rest, opp_rest = ctx.get("rec_rest"), ctx.get("opp_rest")
    h2h = ctx.get("h2h") or []
    plus, minus = ranked_edges(rec_prof, opp_prof)

    league = ctx.get("league") or {}
    lg_prof = league.get("profile") or {"teams": 0, "avg": {}, "rank": {}}
    lg_season = league.get("season") or {"teams": 0, "values": {}, "rank": {}}
    effects = league.get("effects") or {}
    record = league.get("record") or {}
    rec_nba, opp_nba = ctx.get("rec_nba"), ctx.get("opp_nba")
    rec_db, opp_db = ctx.get("rec_db_id"), ctx.get("opp_db_id")
    rec_rank = lg_prof["rank"].get(rec_nba, {}) if rec_nba is not None else {}
    opp_rank = lg_prof["rank"].get(opp_nba, {}) if opp_nba is not None else {}
    n_prof = lg_prof.get("teams", 0)
    rec_srank = lg_season["rank"].get(rec_db, {}) if rec_db is not None else {}
    opp_srank = lg_season["rank"].get(opp_db, {}) if opp_db is not None else {}
    n_season = lg_season.get("teams", 0)
    q = quantify(ctx)
    sigma_note_en = (
        f"measured from {q['sigma_n']} games this season" if q["sigma_measured"]
        else f"the long-run {q['sigma_spread']:.1f}-point spread of NBA results around the line"
    )
    sigma_note_zh = (
        f"以本季 {q['sigma_n']} 場實際結果量得" if q["sigma_measured"]
        else f"採 NBA 長期結果相對盤口的 {q['sigma_spread']:.1f} 分標準差"
    )

    en: List[str] = []
    zh: List[str] = []

    # ---- 1. The call
    en.append("## The Call")
    zh.append("## 結論")
    venue_en = "at home" if rec_home else "on the road"
    venue_zh = "主場" if rec_home else "客場"
    if withheld:
        en.append(
            f"The spread model leans {rec_name} {venue_en}, but the line is {_line(rec_line or 0.0)} "
            f"and our large-underdog rule keeps a pick of that size off the board. Only the total is published here."
        )
        zh.append(
            f"讓分模型偏向{venue_zh}的 {rec_name}，但盤口是 {_line(rec_line or 0.0)}，"
            f"依大受讓規則這種級距不發佈讓分建議。本場只公布大小分。"
        )
    else:
        openers_en = [
            f"{rec_name} {venue_en} is the side.",
            f"We land on {rec_name} {venue_en}.",
            f"The number says {rec_name}, {venue_en}.",
        ]
        openers_zh = [
            f"本場站 {venue_zh}的 {rec_name}。",
            f"結論落在{venue_zh}作戰的 {rec_name}。",
            f"數字指向 {rec_name}（{venue_zh}）。",
        ]
        en.append(rng.choice(openers_en))
        zh.append(rng.choice(openers_zh))
        if has_spread:
            article = "an" if f"{abs(market_rec):.1f}"[0] == "8" or f"{abs(market_rec):.1f}".startswith(("11", "18")) else "a"
            en.append(
                f"The market has {rec} at {_line(rec_line)}, which implies {article} {abs(market_rec):.1f}-point "
                f"{'win' if market_rec > 0 else 'loss'} and a {_pct(q['p_win_market'])} win probability. "
                f"Our projection is {_signed(model_rec)} for {rec} ({_pct(q['p_win_model'])} to win), "
                f"a gap of {abs(edge_pts):.1f} points {'in favour of' if edge_pts > 0 else 'against'} the cover."
            )
            zh.append(
                f"市場開 {rec} {_line(rec_line)}，等於預期{'贏' if market_rec > 0 else '輸'} {abs(market_rec):.1f} 分、"
                f"勝率 {_pct(q['p_win_market'])}；模型估 {rec} {_signed(model_rec)}（勝率 {_pct(q['p_win_model'])}），"
                f"與盤口差 {abs(edge_pts):.1f} 分，{'有利於' if edge_pts > 0 else '不利於'}過盤。"
            )
            en.append(
                f"Converted with {sigma_note_en}, a {abs(edge_pts):.1f}-point edge is a {_pct(q['p_cover'])} chance of covering; "
                f"break-even at standard -110 pricing is 52.4%."
            )
            zh.append(
                f"{sigma_note_zh}換算，{abs(edge_pts):.1f} 分的優勢等於 {_pct(q['p_cover'])} 的過盤機率；"
                f"一般 -110 賠率的損益兩平點是 52.4%。"
            )
        elif spread_home is None:
            en.append(
                f"No spread was posted when this ran, so this is a straight call on the winner: the model has {rec} by "
                f"{abs(model_rec):.1f}, a {_pct(q['p_win_model'])} win probability."
            )
            zh.append(f"執行時還沒有讓分盤口，等於直接選勝方：模型估 {rec} 贏 {abs(model_rec):.1f} 分，勝率 {_pct(q['p_win_model'])}。")
        else:
            en.append(
                f"The line is a pick'em, so this is a straight call on the winner: the model has {rec} by "
                f"{abs(model_rec):.1f}, a {_pct(q['p_win_model'])} win probability."
            )
            zh.append(f"本場平盤，等於直接選勝方：模型估 {rec} 贏 {abs(model_rec):.1f} 分，勝率 {_pct(q['p_win_model'])}。")
        if abs(raw_rec - model_rec) >= 0.8:
            en.append(
                f"Before blending toward the market the raw model number was {_signed(raw_rec)}; "
                f"we pull it 20% toward the line to respect price discovery."
            )
            zh.append(
                f"未向市場收斂前，模型原始值是 {_signed(raw_rec)}；我們固定把它往盤口拉 20%，尊重市場定價。"
            )
        en.append(f"Confidence is {_conf_word(conf, False)} at {conf:.0f}%.")
        zh.append(f"信心{_conf_word(conf, True)}（{conf:.0f}%）。")

    # ---- 2. Season so far
    en.append("## Season So Far")
    zh.append("## 本季至今")
    if rec_form.get("games") and opp_form.get("games"):
        en.append(
            f"{rec} is {_record(rec_form)} ({rec_form['home_record'][0]}-{rec_form['home_record'][1]} home, "
            f"{rec_form['away_record'][0]}-{rec_form['away_record'][1]} away), scoring {rec_form['ppg']:.1f}"
            f"{_rank_note_en(rec_srank.get('ppg'), n_season)} and allowing {rec_form['papg']:.1f}"
            f"{_rank_note_en(rec_srank.get('papg'), n_season)} for a {_signed(rec_form['margin'])} margin"
            f"{_rank_note_en(rec_srank.get('margin'), n_season)}, currently on a {rec_form['streak']} run. "
            f"Last out: {_last_results_en(rec_form)}."
        )
        zh.append(
            f"{rec} 戰績 {_record(rec_form)}（主 {rec_form['home_record'][0]}-{rec_form['home_record'][1]}、"
            f"客 {rec_form['away_record'][0]}-{rec_form['away_record'][1]}），場均得 {rec_form['ppg']:.1f}"
            f"{_rank_note_zh(rec_srank.get('ppg'), n_season)}、失 {rec_form['papg']:.1f}"
            f"{_rank_note_zh(rec_srank.get('papg'), n_season)}，淨勝 {_signed(rec_form['margin'])}"
            f"{_rank_note_zh(rec_srank.get('margin'), n_season)}，目前 {rec_form['streak']}。近況：{_last_results_zh(rec_form)}。"
        )
        en.append(
            f"{opp} is {_record(opp_form)}, scoring {opp_form['ppg']:.1f}{_rank_note_en(opp_srank.get('ppg'), n_season)} and "
            f"allowing {opp_form['papg']:.1f}{_rank_note_en(opp_srank.get('papg'), n_season)} for a "
            f"{_signed(opp_form['margin'])} margin{_rank_note_en(opp_srank.get('margin'), n_season)}, on a {opp_form['streak']} run. "
            f"Last out: {_last_results_en(opp_form)}."
        )
        zh.append(
            f"{opp} 戰績 {_record(opp_form)}，場均得 {opp_form['ppg']:.1f}{_rank_note_zh(opp_srank.get('ppg'), n_season)}、"
            f"失 {opp_form['papg']:.1f}{_rank_note_zh(opp_srank.get('papg'), n_season)}，"
            f"淨勝 {_signed(opp_form['margin'])}{_rank_note_zh(opp_srank.get('margin'), n_season)}，目前 {opp_form['streak']}。"
            f"近況：{_last_results_zh(opp_form)}。"
        )
        bits_en, bits_zh = [], []
        for code, form in ((rec, rec_form), (opp, opp_form)):
            if form.get("ats"):
                w, l, p = form["ats"]
                rate = f" ({_pct(w / (w + l))})" if (w + l) else ""
                bits_en.append(f"{code} {w}-{l}{f'-{p}' if p else ''} against the spread{rate}")
                bits_zh.append(f"{code} 讓分 {w} 勝 {l} 負{f' {p} 和' if p else ''}{rate}")
            if form.get("ou"):
                o, u, p = form["ou"]
                bits_en.append(f"{o} over / {u} under")
                bits_zh.append(f"大分 {o} 次、小分 {u} 次")
        if bits_en:
            en.append("Against the number: " + "; ".join(bits_en) + ".")
            zh.append("對盤口表現：" + "；".join(bits_zh) + "。")
    elif rec_form.get("games") or opp_form.get("games"):
        for code, form in ((rec, rec_form), (opp, opp_form)):
            if form.get("games"):
                en.append(f"{code} has played {form['games']} ({_record(form)}): {_last_results_en(form)}.")
                zh.append(f"{code} 已打 {form['games']} 場（{_record(form)}）：{_last_results_zh(form)}。")
            else:
                en.append(f"{code} has not played yet this season, so its profile below carries more weight.")
                zh.append(f"{code} 本季尚未出賽，下方的數據體質佔較大比重。")
    else:
        en.append(
            "Neither team has a completed game on the books yet, so this read leans on the statistical profile "
            "each side brings into the season rather than current results."
        )
        zh.append("兩隊本季都還沒有完賽紀錄，這份判讀主要靠雙方帶進本季的數據體質，而不是當下戰績。")

    if h2h:
        wins = sum(1 for g in h2h if g["won"])
        avg_margin = sum(g["for"] - g["against"] for g in h2h) / len(h2h)
        en.append(
            f"Head to head, {rec} is {wins}-{len(h2h) - wins} in the last {len(h2h)} meetings with an average margin of "
            f"{_signed(avg_margin)} (most recent {h2h[-1]['date']}: {'W' if h2h[-1]['won'] else 'L'} "
            f"{h2h[-1]['for']}-{h2h[-1]['against']})."
        )
        zh.append(
            f"近 {len(h2h)} 次交手 {rec} {wins} 勝 {len(h2h) - wins} 負，平均分差 {_signed(avg_margin)}"
            f"（最近一次 {h2h[-1]['date']}：{'勝' if h2h[-1]['won'] else '負'} {h2h[-1]['for']}-{h2h[-1]['against']}）。"
        )

    # ---- 3. Statistical profile
    en.append("## Statistical Profile")
    zh.append("## 數據體質")
    if rec_prof and opp_prof:
        stale_en = stale_zh = ""
        today = ctx.get("date")
        try:
            if today and (date_type.fromisoformat(today[:10]) - rec_prof["last_date"]).days > 21:
                stale_en = f" (box scores on record through {rec_prof['last_date'].isoformat()})"
                stale_zh = f"（有紀錄的比賽資料到 {rec_prof['last_date'].isoformat()}）"
        except (TypeError, ValueError):
            pass
        n = rec_prof["games"]
        lg_tail_en = f" League averages and ranks across {n_prof} teams are given for scale." if n_prof else ""
        lg_tail_zh = f"括號內是 {n_prof} 隊的聯盟平均與排名，方便對照。" if n_prof else ""
        lead_en = [
            f"Over the last {n} games on record{stale_en}, {rec}'s edges are concrete rather than cosmetic.{lg_tail_en}",
            f"Across the last {n} box scores{stale_en}, here is where {rec} separates from {opp}.{lg_tail_en}",
            f"The {n}-game profile{stale_en} explains most of the projection.{lg_tail_en}",
        ]
        lead_zh = [
            f"看近 {n} 場有紀錄的比賽{stale_zh}，{rec} 的優勢是實打實的數字，不是印象。{lg_tail_zh}",
            f"近 {n} 場技術統計{stale_zh}裡，{rec} 和 {opp} 拉開差距的地方在這幾項。{lg_tail_zh}",
            f"近 {n} 場的數據體質{stale_zh}解釋了大部分的預測結果。{lg_tail_zh}",
        ]

        def lg_en(key, fmt):
            avg = lg_prof["avg"].get(key)
            r_rec, r_opp = rec_rank.get(key), opp_rank.get(key)
            parts = []
            if avg is not None:
                parts.append(f"league avg {_f(avg, fmt)}")
            if r_rec and r_opp:
                parts.append(f"{rec} {_ordinal(r_rec)} vs {opp} {_ordinal(r_opp)} of {n_prof}")
            return f" ({'; '.join(parts)})" if parts else ""

        def lg_zh(key, fmt):
            avg = lg_prof["avg"].get(key)
            r_rec, r_opp = rec_rank.get(key), opp_rank.get(key)
            parts = []
            if avg is not None:
                parts.append(f"聯盟平均 {_f(avg, fmt)}")
            if r_rec and r_opp:
                parts.append(f"{rec} 第 {r_rec}、{opp} 第 {r_opp}／{n_prof} 隊")
            return f"（{'；'.join(parts)}）" if parts else ""

        if plus:
            en.append(rng.choice(lead_en))
            zh.append(rng.choice(lead_zh))
            for key, _z, rv, ov in plus[:4]:
                _k, _c, label_en, label_zh, _b, _s, fmt = _stat_meta(key)
                en.append(f"• **{label_en}** — {rec} {NARRATIVE_EN[key].format(rec=_f(rv, fmt), opp=_f(ov, fmt))}{lg_en(key, fmt)}.")
                zh.append(f"• **{label_zh}**：{rec} {NARRATIVE_ZH[key].format(rec=_f(rv, fmt), opp=_f(ov, fmt))}{lg_zh(key, fmt)}。")
        else:
            en.append(
                f"The last {n} games on record{stale_en} show no category where {rec} clearly separates from {opp}; "
                f"the projection is being driven by the broader rolling windows and the matchup context rather than one headline stat."
            )
            zh.append(
                f"近 {n} 場有紀錄的比賽{stale_zh}裡，{rec} 沒有哪一項明顯壓過 {opp}；"
                f"預測主要來自更長的滾動窗口與對戰情境，不是單一亮眼數據。"
            )
        if minus:
            en.append(f"Where {opp} pushes back:")
            zh.append(f"{opp} 能反擊的地方：")
            for key, _z, rv, ov in minus[:3]:
                _k, _c, label_en, label_zh, _b, _s, fmt = _stat_meta(key)
                en.append(f"• **{label_en}** — {opp} holds the better number, {_f(ov, fmt)} to {rec}'s {_f(rv, fmt)}{lg_en(key, fmt)}.")
                zh.append(f"• **{label_zh}**：{opp} 這項較好，{_f(ov, fmt)} 對 {rec} 的 {_f(rv, fmt)}{lg_zh(key, fmt)}。")
        if rec_prof.get("margin_sd") is not None and opp_prof.get("margin_sd") is not None:
            en.append(
                f"Consistency check: {rec}'s game margins over this stretch vary by ±{rec_prof['margin_sd']:.1f} points "
                f"(one standard deviation) against ±{opp_prof['margin_sd']:.1f} for {opp}; "
                f"the {'steadier' if rec_prof['margin_sd'] < opp_prof['margin_sd'] else 'more volatile'} side is {rec}."
            )
            zh.append(
                f"穩定度：這段期間 {rec} 單場分差的標準差是 ±{rec_prof['margin_sd']:.1f} 分，{opp} 是 ±{opp_prof['margin_sd']:.1f} 分；"
                f"{rec} 的表現{'較穩' if rec_prof['margin_sd'] < opp_prof['margin_sd'] else '起伏較大'}。"
            )
    else:
        en.append("Box-score profiles are not available for both teams, so this section is skipped.")
        zh.append("兩隊的技術統計不齊，這一段略過。")

    # ---- 4. Schedule and rest
    en.append("## Schedule & Rest")
    zh.append("## 賽程與休息")
    rest_bits_en, rest_bits_zh = [], []
    for code, r in ((rec, rec_rest), (opp, opp_rest)):
        if r is None:
            continue
        if r <= 1:
            rest_bits_en.append(f"{code} is on the second night of a back-to-back")
            rest_bits_zh.append(f"{code} 背靠背第二戰")
        elif r == 2:
            rest_bits_en.append(f"{code} has one day off")
            rest_bits_zh.append(f"{code} 休一天")
        else:
            rest_bits_en.append(f"{code} comes in with {r - 1} days of rest")
            rest_bits_zh.append(f"{code} 休了 {r - 1} 天")
    if rest_bits_en:
        en.append("; ".join(rest_bits_en) + ".")
        zh.append("；".join(rest_bits_zh) + "。")
        if rec_rest is not None and opp_rest is not None and rec_rest != opp_rest:
            fresher = rec if rec_rest > opp_rest else opp
            en.append(f"The rest edge belongs to {fresher}.")
            zh.append(f"體能上 {fresher} 較佔便宜。")
    else:
        en.append("No recent game on file for either side, so rest is not a factor in this read.")
        zh.append("兩隊近期都沒有可比的出賽紀錄，休息天數不列入考量。")
    any_b2b = (rec_rest is not None and rec_rest <= 1) or (opp_rest is not None and opp_rest <= 1)
    if any_b2b and effects.get("b2b_n"):
        en.append(
            f"How much that matters: over the last {effects['years']} seasons, teams on the second night of a back-to-back have been outscored by "
            f"{abs(effects['b2b_margin']):.1f} points per game and won {_pct(effects['b2b_win_rate'])} of the time "
            f"(n = {effects['b2b_n']:,} team-games)."
        )
        zh.append(
            f"量化來看：近 {effects['years']} 季背靠背第二戰的球隊平均每場被淨勝 {abs(effects['b2b_margin']):.1f} 分，"
            f"勝率 {_pct(effects['b2b_win_rate'])}（樣本 {effects['b2b_n']:,} 隊次）。"
        )
    home_code = ctx.get("home_code") or (rec if rec_home else opp)
    if effects.get("home_n"):
        en.append(
            f"{home_code} has the floor. Home teams have outscored visitors by {_signed(effects['home_margin'])} per game and won "
            f"{_pct(effects['home_win_rate'])} of games over the last {effects['years']} seasons (n = {effects['home_n']:,})"
            + ("; that is already priced into the line, so it does not move our number on its own." if has_spread else ".")
        )
        zh.append(
            f"{home_code} 坐擁主場。近 {effects['years']} 季主隊平均淨勝 {_signed(effects['home_margin'])} 分、勝率 "
            f"{_pct(effects['home_win_rate'])}（樣本 {effects['home_n']:,} 場）"
            + ("；這已反映在盤口裡，不會單獨改變我們的數字。" if has_spread else "。")
        )
    else:
        en.append(
            f"{home_code} has the floor. Home court is already priced into the line, so it does not move our number on its own."
            if has_spread else f"{home_code} has the floor."
        )
        zh.append(
            f"{home_code} 坐擁主場。主場優勢已反映在盤口裡，不會單獨改變我們的數字。"
            if has_spread else f"{home_code} 坐擁主場。"
        )

    # ---- 5. Total
    en.append(f"## Total: {ou} {float(total_line):.1f}" if total_line is not None else "## Total")
    zh.append(f"## 大小分：{'大分' if ou == 'OVER' else '小分'} {float(total_line):.1f}" if total_line is not None else "## 大小分")
    if total_default:
        en.append(
            "No posted total was available at run time, so the 225.0 reference is a placeholder and the lean below should be treated as directional only."
        )
        zh.append("執行時沒有公布的大小分盤口，225.0 只是參考值，下面的判斷僅供方向參考。")
    tempo_bits_en, tempo_bits_zh = [], []
    if rec_form.get("games") and opp_form.get("games"):
        combined = rec_form["ppg"] + opp_form["ppg"]
        allowed = rec_form["papg"] + opp_form["papg"]
        tempo_bits_en.append(
            f"this season the two offences combine for {combined:.1f} points and the two defences concede {allowed:.1f}"
        )
        tempo_bits_zh.append(f"本季兩隊進攻合計 {combined:.1f} 分，防守合計失 {allowed:.1f} 分")
    if rec_prof and opp_prof and rec_prof.get("tpa") is not None and opp_prof.get("tpa") is not None:
        tpa_avg = lg_prof["avg"].get("tpa")
        fb_avg = lg_prof["avg"].get("fb")
        tpa_note_en = f" (league pair average {2 * tpa_avg:.0f})" if tpa_avg else ""
        fb_note_en = f" (league pair average {2 * fb_avg:.0f})" if fb_avg else ""
        tempo_bits_en.append(
            f"on record they attempt {rec_prof['tpa'] + opp_prof['tpa']:.0f} threes between them{tpa_note_en} with "
            f"{rec_prof['fb'] + opp_prof['fb']:.0f} fast-break points{fb_note_en}"
        )
        tempo_bits_zh.append(
            f"近況合計每場出手 {rec_prof['tpa'] + opp_prof['tpa']:.0f} 記三分"
            f"{f'（聯盟兩隊平均 {2 * tpa_avg:.0f}）' if tpa_avg else ''}、快攻 {rec_prof['fb'] + opp_prof['fb']:.0f} 分"
            f"{f'（聯盟兩隊平均 {2 * fb_avg:.0f}）' if fb_avg else ''}"
        )
    if effects.get("avg_total"):
        tempo_bits_en.append(f"the league-wide average total over the last {effects['years']} seasons is {effects['avg_total']:.1f}")
        tempo_bits_zh.append(f"近 {effects['years']} 季聯盟平均總分 {effects['avg_total']:.1f}")
    if tempo_bits_en:
        en.append("Tempo check: " + "; ".join(tempo_bits_en) + ".")
        zh.append("節奏觀察：" + "；".join(tempo_bits_zh) + "。")
    if total_line is not None:
        p_total = q["p_total"]
        en.append(
            f"The model projects {pred_total:.1f} total points against a line of {float(total_line):.1f}, "
            f"{abs(total_edge):.1f} points {'above' if total_edge > 0 else 'below'} the number. "
            f"With totals spreading ±{q['sigma_total']:.1f} points around the line, that is a {_pct(p_total)} probability of the "
            f"{ou.lower()}; published confidence is {ou_conf:.0f}%."
        )
        zh.append(
            f"模型預測總分 {pred_total:.1f}，盤口 {float(total_line):.1f}，{'高' if total_edge > 0 else '低'}於盤口 {abs(total_edge):.1f} 分。"
            f"以總分相對盤口 ±{q['sigma_total']:.1f} 分的分佈換算，{'大分' if ou == 'OVER' else '小分'}機率 {_pct(p_total)}；"
            f"公布信心 {ou_conf:.0f}%。"
        )
    else:
        en.append(f"The model projects {pred_total:.1f} total points.")
        zh.append(f"模型預測總分 {pred_total:.1f}。")

    # ---- 6. Track record
    sp, tt = record.get("spread") or {}, record.get("total") or {}
    sp_n, tt_n = sp.get("w", 0) + sp.get("l", 0), tt.get("w", 0) + tt.get("l", 0)
    if sp_n or tt_n:
        en.append("## Model Track Record")
        zh.append("## 模型本季戰績")
        bits_en, bits_zh = [], []
        if sp_n:
            bits_en.append(f"published spread picks are {sp['w']}-{sp['l']} ({_pct(sp['w'] / sp_n)})")
            bits_zh.append(f"已發佈讓分 {sp['w']} 勝 {sp['l']} 負（{_pct(sp['w'] / sp_n)}）")
            band = record.get("spread_at_conf") or {}
            band_n = band.get("w", 0) + band.get("l", 0)
            if band_n >= 3 and not withheld:
                bits_en.append(f"at {conf:.0f}%+ confidence they are {band['w']}-{band['l']}")
                bits_zh.append(f"信心 {conf:.0f}% 以上的場次 {band['w']} 勝 {band['l']} 負")
        if tt_n:
            bits_en.append(f"totals are {tt['w']}-{tt['l']} ({_pct(tt['w'] / tt_n)})")
            bits_zh.append(f"大小分 {tt['w']} 勝 {tt['l']} 負（{_pct(tt['w'] / tt_n)}）")
        small_en = " The sample is still small; treat these as a progress report, not a guarantee." if max(sp_n, tt_n) < 30 else ""
        small_zh = "樣本還小，這是進度回報，不是保證。" if max(sp_n, tt_n) < 30 else ""
        en.append("This season, " + "; ".join(bits_en) + f".{small_en}")
        zh.append("本季至今，" + "；".join(bits_zh) + f"。{small_zh}")

    # ---- 7. Risk
    en.append("## What Could Go Wrong")
    zh.append("## 風險")
    risks_en, risks_zh = [], []
    if not withheld and has_spread and abs(edge_pts) < 1.5:
        risks_en.append(f"the edge is only {abs(edge_pts):.1f} points ({_pct(q['p_cover'])} cover probability), inside normal line noise")
        risks_zh.append(f"優勢只有 {abs(edge_pts):.1f} 分（過盤機率 {_pct(q['p_cover'])}），落在盤口正常波動範圍內")
    if rec_line is not None and rec_line <= -8:
        risks_en.append(f"laying {abs(rec_line):.1f} asks {rec} to win comfortably, not just win")
        risks_zh.append(f"讓 {abs(rec_line):.1f} 分代表 {rec} 不只要贏，還要贏得輕鬆")
    if rec_line is not None and rec_line >= 8 and not withheld:
        risks_en.append(f"taking {_line(rec_line)} relies on {rec} staying within reach late")
        risks_zh.append(f"收 {_line(rec_line)} 的前提是 {rec} 末段還咬得住")
    if minus:
        key = minus[0][0]
        _k, _c, label_en, label_zh, _b, _s, fmt = _stat_meta(key)
        risks_en.append(f"{opp}'s edge in {label_en} ({_f(minus[0][3], fmt)} vs {_f(minus[0][2], fmt)}) is the cleanest path to an upset of this read")
        risks_zh.append(f"{opp} 在{label_zh}上的優勢（{_f(minus[0][3], fmt)} 對 {_f(minus[0][2], fmt)}）是翻掉這份判讀最直接的路徑")
    if rec_rest is not None and rec_rest <= 1:
        risks_en.append(f"{rec} is playing tired legs on a back-to-back")
        risks_zh.append(f"{rec} 背靠背，體能是變數")
    if rec_prof and rec_prof.get("margin_sd") and rec_prof["margin_sd"] >= 14:
        risks_en.append(f"{rec}'s results swing ±{rec_prof['margin_sd']:.1f} points game to game, so any single-game edge is fragile")
        risks_zh.append(f"{rec} 單場分差起伏 ±{rec_prof['margin_sd']:.1f} 分，單場優勢並不牢靠")
    if rec_form.get("games") and rec_form.get("streak", "").startswith("L") and int(rec_form["streak"][1:]) >= 2:
        risks_en.append(f"{rec} is on a {rec_form['streak']} skid and the model does not read locker rooms")
        risks_zh.append(f"{rec} 正吞 {rec_form['streak'][1:]} 連敗，模型看不到更衣室氣氛")
    if (rec_form.get("games") or 0) < 3 and (opp_form.get("games") or 0) < 3:
        risks_en.append("sample sizes this early in the season are thin and roster changes are not in the box scores yet")
        risks_zh.append("季初樣本很小，陣容異動也還沒反映在技術統計裡")
    if raw_rec * model_rec < 0:
        risks_en.append("the raw model and the market-blended number disagree on the side; the published lean is the blended one")
        risks_zh.append("模型原始值和向市場收斂後的數字方向相反，這裡公布的是收斂後的版本")
    if not risks_en:
        risks_en.append("no single factor stands out; the main risk is variance in a 48-minute sample")
        risks_zh.append("沒有單一明顯風險，主要變數是單場 48 分鐘的隨機性")
    en.append("Honest caveats: " + "; ".join(risks_en) + ".")
    zh.append("坦白說：" + "；".join(risks_zh) + "。")

    facts = _facts(ctx, rec_prof, opp_prof, rec_form, opp_form, rec_rest, opp_rest, h2h,
                   model_rec, raw_rec, market_rec, pred_total, total_line, total_default,
                   q, lg_prof, rec_rank, opp_rank, rec_srank, opp_srank, n_season, effects, record)
    return "\n".join(en), "\n".join(zh), facts


def _facts(ctx, rec_prof, opp_prof, rec_form, opp_form, rec_rest, opp_rest, h2h,
           model_rec, raw_rec, market_rec, pred_total, total_line, total_default,
           q, lg_prof, rec_rank, opp_rank, rec_srank, opp_srank, n_season, effects, record) -> dict:
    rows = []
    if rec_prof and opp_prof:
        for key, _col, label_en, label_zh, better, _scale, fmt in STAT_ROWS:
            rv, ov = rec_prof.get(key), opp_prof.get(key)
            if rv is None or ov is None or np.isnan(rv) or np.isnan(ov):
                continue
            avg = lg_prof["avg"].get(key)
            scale = 100 if fmt == "pct" else 1
            rows.append({
                "key": key, "en": label_en, "zh": label_zh,
                "rec": round(rv * scale, 1), "opp": round(ov * scale, 1),
                "avg": round(avg * scale, 1) if avg is not None else None,
                "rec_rank": rec_rank.get(key), "opp_rank": opp_rank.get(key),
                "unit": "%" if fmt == "pct" else "",
                "better": better,
            })

    def form_public(form, rest, srank):
        if not form.get("games"):
            return {"games": 0, "rest": rest}
        return {
            "games": form["games"], "wins": form["wins"], "losses": form["losses"],
            "home": list(form["home_record"]), "away": list(form["away_record"]),
            "ppg": round(form["ppg"], 1), "papg": round(form["papg"], 1), "margin": round(form["margin"], 1),
            "rank": {k: srank.get(k) for k in ("ppg", "papg", "margin")},
            "streak": form["streak"], "ats": list(form["ats"]) if form.get("ats") else None,
            "ou": list(form["ou"]) if form.get("ou") else None, "rest": rest,
        }

    sp, tt = record.get("spread") or {}, record.get("total") or {}
    return {
        "profile_games": rec_prof["games"] if rec_prof else 0,
        "profile_through": rec_prof["last_date"].isoformat() if rec_prof else None,
        "league_teams": lg_prof.get("teams", 0),
        "season_teams": n_season,
        "rows": rows,
        "form": {"rec": form_public(rec_form, rec_rest, rec_srank), "opp": form_public(opp_form, opp_rest, opp_srank)},
        "volatility": {
            "rec": round(rec_prof["margin_sd"], 1) if rec_prof and rec_prof.get("margin_sd") is not None else None,
            "opp": round(opp_prof["margin_sd"], 1) if opp_prof and opp_prof.get("margin_sd") is not None else None,
        },
        "h2h": h2h,
        "projection": {
            "model_margin": round(model_rec, 1),
            "raw_margin": round(raw_rec, 1),
            "market_margin": round(market_rec, 1),
            "edge": round(model_rec - market_rec, 1),
            "pred_total": round(pred_total, 1),
            "total_line": float(total_line) if total_line is not None else None,
            "total_edge": round(pred_total - float(total_line), 1) if total_line is not None else None,
            "total_is_default": total_default,
        },
        "probability": {
            "cover": round(q["p_cover"], 3),
            "win_model": round(q["p_win_model"], 3),
            "win_market": round(q["p_win_market"], 3) if q["p_win_market"] is not None else None,
            "total": round(q["p_total"], 3) if q["p_total"] is not None else None,
            "sigma_spread": q["sigma_spread"], "sigma_total": q["sigma_total"],
            "sigma_measured": q["sigma_measured"],
        },
        "effects": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in effects.items()},
        "record": {
            "spread": [sp.get("w", 0), sp.get("l", 0)],
            "total": [tt.get("w", 0), tt.get("l", 0)],
            "spread_at_conf": [record["spread_at_conf"].get("w", 0), record["spread_at_conf"].get("l", 0)] if record.get("spread_at_conf") else None,
        },
        "generated_at": datetime.utcnow().isoformat(timespec="seconds"),
    }
