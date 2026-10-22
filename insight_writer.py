"""Research-style match write-ups from the numbers the picker already has.

Everything here is derived from data on hand: this season's results in SQLite,
the box-score profile in TeamStatistics.csv, the posted lines, and the model's
own projection. No external calls. Output is a bilingual text (section headers
start with "## ", bullets with "• ") plus a facts dict the detail page renders
as a comparison table.
"""
from __future__ import annotations

import random
from datetime import date as date_type
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

FINISHED = ("STATUS_FINISHED", "STATUS_FINAL", "Final")
PROFILE_GAMES = 10

LOG_COLS = [
    "gameDateTimeEst", "teamId", "opponentTeamId", "home", "win", "teamScore", "opponentScore",
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


def team_profile(logs: pd.DataFrame, nba_team_id: int, games: int = PROFILE_GAMES) -> Optional[dict]:
    if logs is None or logs.empty:
        return None
    sub = logs[logs["teamId"] == int(nba_team_id)].tail(games)
    if sub.empty:
        return None
    out = {"games": int(len(sub)), "last_date": sub["gameDateTimeEst"].max().date()}
    for key, col, *_ in STAT_ROWS:
        out[key] = float(pd.to_numeric(sub[col], errors="coerce").mean()) if col in sub.columns else None
    if "win" in sub.columns:
        wins = pd.to_numeric(sub["win"], errors="coerce").fillna(0)
        out["win_rate"] = float(wins.mean())
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
            article = "an" if f"{abs(market_rec):.1f}"[0] in "8" or f"{abs(market_rec):.1f}".startswith(("11", "18")) else "a"
            en.append(
                f"The market has {rec} at {_line(rec_line)}, which implies {article} {abs(market_rec):.1f}-point "
                f"{'win' if market_rec > 0 else 'loss'}. Our projection is {_signed(model_rec)} for {rec}, "
                f"a gap of {abs(edge_pts):.1f} points {'in favour of' if edge_pts > 0 else 'against'} the cover."
            )
            zh.append(
                f"市場開 {rec} {_line(rec_line)}，等於預期{'贏' if market_rec > 0 else '輸'} {abs(market_rec):.1f} 分；"
                f"模型估 {rec} {_signed(model_rec)}，與盤口差 {abs(edge_pts):.1f} 分，"
                f"{'有利於' if edge_pts > 0 else '不利於'}過盤。"
            )
        elif spread_home is None:
            en.append(
                f"No spread was posted when this ran, so this is a straight call on the winner: the model has {rec} by "
                f"{abs(model_rec):.1f}."
            )
            zh.append(f"執行時還沒有讓分盤口，等於直接選勝方：模型估 {rec} 贏 {abs(model_rec):.1f} 分。")
        else:
            en.append(
                f"The line is a pick'em, so this is a straight call on the winner: the model has {rec} by "
                f"{abs(model_rec):.1f}."
            )
            zh.append(f"本場平盤，等於直接選勝方：模型估 {rec} 贏 {abs(model_rec):.1f} 分。")
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
            f"{rec_form['away_record'][0]}-{rec_form['away_record'][1]} away), scoring {rec_form['ppg']:.1f} and "
            f"allowing {rec_form['papg']:.1f} for a {_signed(rec_form['margin'])} margin, currently on a {rec_form['streak']} run. "
            f"Last out: {_last_results_en(rec_form)}."
        )
        zh.append(
            f"{rec} 戰績 {_record(rec_form)}（主 {rec_form['home_record'][0]}-{rec_form['home_record'][1]}、"
            f"客 {rec_form['away_record'][0]}-{rec_form['away_record'][1]}），場均得 {rec_form['ppg']:.1f}、失 {rec_form['papg']:.1f}，"
            f"淨勝 {_signed(rec_form['margin'])}，目前 {rec_form['streak']}。近況：{_last_results_zh(rec_form)}。"
        )
        en.append(
            f"{opp} is {_record(opp_form)}, {opp_form['ppg']:.1f} for and {opp_form['papg']:.1f} against "
            f"({_signed(opp_form['margin'])}), on a {opp_form['streak']} run. Last out: {_last_results_en(opp_form)}."
        )
        zh.append(
            f"{opp} 戰績 {_record(opp_form)}，場均得 {opp_form['ppg']:.1f}、失 {opp_form['papg']:.1f}"
            f"（{_signed(opp_form['margin'])}），目前 {opp_form['streak']}。近況：{_last_results_zh(opp_form)}。"
        )
        bits_en, bits_zh = [], []
        for code, form in ((rec, rec_form), (opp, opp_form)):
            if form.get("ats"):
                w, l, p = form["ats"]
                bits_en.append(f"{code} {w}-{l}{f'-{p}' if p else ''} against the spread")
                bits_zh.append(f"{code} 讓分 {w} 勝 {l} 負{f' {p} 和' if p else ''}")
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
        lead_en = [
            f"Over the last {n} games on record{stale_en}, {rec}'s edges are concrete rather than cosmetic.",
            f"Across the last {n} box scores{stale_en}, here is where {rec} separates from {opp}.",
            f"The {n}-game profile{stale_en} explains most of the projection.",
        ]
        lead_zh = [
            f"看近 {n} 場有紀錄的比賽{stale_zh}，{rec} 的優勢是實打實的數字，不是印象。",
            f"近 {n} 場技術統計{stale_zh}裡，{rec} 和 {opp} 拉開差距的地方在這幾項。",
            f"近 {n} 場的數據體質{stale_zh}解釋了大部分的預測結果。",
        ]
        if plus:
            en.append(rng.choice(lead_en))
            zh.append(rng.choice(lead_zh))
            for key, _z, rv, ov in plus[:4]:
                _k, _c, label_en, label_zh, _b, _s, fmt = _stat_meta(key)
                en.append(f"• **{label_en}** — {rec} {NARRATIVE_EN[key].format(rec=_f(rv, fmt), opp=_f(ov, fmt))}.")
                zh.append(f"• **{label_zh}**：{rec} {NARRATIVE_ZH[key].format(rec=_f(rv, fmt), opp=_f(ov, fmt))}。")
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
                en.append(f"• **{label_en}** — {opp} holds the better number, {_f(ov, fmt)} to {rec}'s {_f(rv, fmt)}.")
                zh.append(f"• **{label_zh}**：{opp} 這項較好，{_f(ov, fmt)} 對 {rec} 的 {_f(rv, fmt)}。")
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
    home_code = ctx.get("home_code") or (rec if rec_home else opp)
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
        tempo_bits_en.append(
            f"on record they attempt {rec_prof['tpa'] + opp_prof['tpa']:.0f} threes between them with "
            f"{rec_prof['fb'] + opp_prof['fb']:.0f} fast-break points"
        )
        tempo_bits_zh.append(
            f"近況合計每場出手 {rec_prof['tpa'] + opp_prof['tpa']:.0f} 記三分、快攻 {rec_prof['fb'] + opp_prof['fb']:.0f} 分"
        )
    if tempo_bits_en:
        en.append("Tempo check: " + "; ".join(tempo_bits_en) + ".")
        zh.append("節奏觀察：" + "；".join(tempo_bits_zh) + "。")
    if total_line is not None:
        en.append(
            f"The model projects {pred_total:.1f} total points against a line of {float(total_line):.1f}, "
            f"{abs(total_edge):.1f} points {'above' if total_edge > 0 else 'below'} the number. "
            f"That is the {ou.lower()} at {ou_conf:.0f}% confidence."
        )
        zh.append(
            f"模型預測總分 {pred_total:.1f}，盤口 {float(total_line):.1f}，{'高' if total_edge > 0 else '低'}於盤口 {abs(total_edge):.1f} 分。"
            f"判斷{'大分' if ou == 'OVER' else '小分'}，信心 {ou_conf:.0f}%。"
        )
    else:
        en.append(f"The model projects {pred_total:.1f} total points.")
        zh.append(f"模型預測總分 {pred_total:.1f}。")

    # ---- 6. Risk
    en.append("## What Could Go Wrong")
    zh.append("## 風險")
    risks_en, risks_zh = [], []
    if not withheld and has_spread and abs(edge_pts) < 1.5:
        risks_en.append(f"the edge is only {abs(edge_pts):.1f} points, inside normal line noise")
        risks_zh.append(f"優勢只有 {abs(edge_pts):.1f} 分，落在盤口正常波動範圍內")
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
                   model_rec, raw_rec, market_rec, pred_total, total_line, total_default)
    return "\n".join(en), "\n".join(zh), facts


def _facts(ctx, rec_prof, opp_prof, rec_form, opp_form, rec_rest, opp_rest, h2h,
           model_rec, raw_rec, market_rec, pred_total, total_line, total_default) -> dict:
    rows = []
    if rec_prof and opp_prof:
        for key, _col, label_en, label_zh, better, _scale, fmt in STAT_ROWS:
            rv, ov = rec_prof.get(key), opp_prof.get(key)
            if rv is None or ov is None or np.isnan(rv) or np.isnan(ov):
                continue
            rows.append({
                "key": key, "en": label_en, "zh": label_zh,
                "rec": round(rv * 100, 1) if fmt == "pct" else round(rv, 1),
                "opp": round(ov * 100, 1) if fmt == "pct" else round(ov, 1),
                "unit": "%" if fmt == "pct" else "",
                "better": better,
            })

    def form_public(form, rest):
        if not form.get("games"):
            return {"games": 0, "rest": rest}
        return {
            "games": form["games"], "wins": form["wins"], "losses": form["losses"],
            "home": list(form["home_record"]), "away": list(form["away_record"]),
            "ppg": round(form["ppg"], 1), "papg": round(form["papg"], 1), "margin": round(form["margin"], 1),
            "streak": form["streak"], "ats": list(form["ats"]) if form.get("ats") else None,
            "ou": list(form["ou"]) if form.get("ou") else None, "rest": rest,
        }

    return {
        "profile_games": rec_prof["games"] if rec_prof else 0,
        "profile_through": rec_prof["last_date"].isoformat() if rec_prof else None,
        "rows": rows,
        "form": {"rec": form_public(rec_form, rec_rest), "opp": form_public(opp_form, opp_rest)},
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
        "generated_at": datetime.utcnow().isoformat(timespec="seconds"),
    }
