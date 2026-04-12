"""
離線模擬：對已結算 spread 套用「降大受讓風險」類政策，對照基準命中率與保留筆數。

  python scripts/simulate_spread_policies.py --picks .../aggregated_picks_rows.csv --matches .../matches_rows.csv --days 90

政策為示意，可改門檻後重跑；不修改資料庫。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from evaluate_aggregated_picks import (
    filter_finished_matches,
    load_picks,
    normalize_matches_columns,
    pick_spread_probability,
    role_favorite_underdog,
)


def build_spread_merged(picks_path: Path, matches_path: Path, days: int | None) -> pd.DataFrame:
    picks = load_picks(picks_path, days)
    sp = picks[picks["spread_outcome"].isin(["WIN", "LOSS"])].copy()
    m = normalize_matches_columns(pd.read_csv(matches_path, low_memory=False))
    need = {"match_id", "home_team_id", "away_team_id", "home_score", "away_score"}
    if not need.issubset(m.columns):
        raise SystemExit(f"matches 缺少欄位: {sorted(need - set(m.columns))}")
    cols = list(need)
    if "status" in m.columns:
        cols.append("status")
    m = m[cols].drop_duplicates(subset=["match_id"])
    m = filter_finished_matches(m)
    merged = sp.merge(m, on="match_id", how="inner")
    merged["role"] = merged.apply(role_favorite_underdog, axis=1)
    merged["abs_line"] = merged["line_info"].astype(float).abs()
    merged["y"] = (merged["spread_outcome"] == "WIN").astype(int)
    merged["p"] = merged.apply(lambda r: pick_spread_probability(r), axis=1)
    return merged


def summarize(name: str, df: pd.DataFrame, mask: pd.Series) -> dict:
    sub = df.loc[mask]
    n = len(sub)
    if n == 0:
        return {"policy": name, "n": 0, "hit": float("nan"), "excluded": len(df) - n}
    return {
        "policy": name,
        "n": n,
        "hit": float(sub["y"].mean()),
        "excluded": int((~mask).sum()),
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description="Spread 政策離線模擬")
    ap.add_argument("--picks", type=Path, required=True)
    ap.add_argument("--matches", type=Path, required=True)
    ap.add_argument("--days", type=int, default=None)
    args = ap.parse_args()

    df = build_spread_merged(args.picks, args.matches, args.days)
    n0 = len(df)
    base_hit = df["y"].mean()

    conf = df["confidence_score"].fillna(0).astype(float)

    policies: list[tuple[str, pd.Series]] = []

    # 1) 基準：全部保留
    policies.append(("A. 基準（不篩選）", pd.Series(True, index=df.index)))

    # 2) 大受讓直接不採信：受讓 且 |line|≥12 排除（與 aggregate_picks 政策 B 一致）
    policies.append(
        (
            "B. 排除「受讓且 |line|≥12」",
            ~((df["role"] == "underdog") & (df["abs_line"] >= 12)),
        )
    )

    # 3) 稍嚴：受讓 且 |line|≥8 排除
    policies.append(
        (
            "C. 排除「受讓且 |line|≥8」",
            ~((df["role"] == "underdog") & (df["abs_line"] >= 8)),
        )
    )

    # 4) 大受讓僅保留高信心（其餘視為不採納 spread）
    policies.append(
        (
            "D. 受讓且 |line|≥12 時，僅 confidence≥72 保留",
            ~(((df["role"] == "underdog") & (df["abs_line"] >= 12)) & (conf < 72)),
        )
    )

    policies.append(
        (
            "E. 受讓且 |line|≥12 時，僅 confidence≥80 保留",
            ~(((df["role"] == "underdog") & (df["abs_line"] >= 12)) & (conf < 80)),
        )
    )

    # 5) 機率 proxy：受讓且 |line|≥8 需 p≥0.55（無 p 則以 confidence 推估，已在 p 欄）
    p_ok = df["p"].fillna(conf / 100.0)
    policies.append(
        (
            "F. 受讓且 |line|≥8 時，需 預測機率 proxy≥0.55",
            ~(((df["role"] == "underdog") & (df["abs_line"] >= 8)) & (p_ok < 0.55)),
        )
    )

    policies.append(
        (
            "G. 受讓且 |line|≥8 時，需 預測機率 proxy≥0.60",
            ~(((df["role"] == "underdog") & (df["abs_line"] >= 8)) & (p_ok < 0.60)),
        )
    )

    # 6) 極端盤：|line|≥14 且受讓一律排除（比生產政策 B 更嚴）
    policies.append(
        (
            "H. 排除「受讓且 |line|≥14」",
            ~((df["role"] == "underdog") & (df["abs_line"] >= 14)),
        )
    )

    # 7) 組合：B + 讓分方全保留（與 B 相同條件，另列一條說明「只砍大受讓」）
    policies.append(
        (
            "I. 組合：排除受讓|line|≥12，且受讓|line|∈[8,12) 需 confidence≥65",
            ~(
                ((df["role"] == "underdog") & (df["abs_line"] >= 12))
                | (((df["role"] == "underdog") & (df["abs_line"] >= 8) & (df["abs_line"] < 12)) & (conf < 65))
            ),
        )
    )

    print("=" * 72)
    print("Spread 政策離線模擬（僅展示；未改 production）")
    print("=" * 72)
    print(f"合併樣本數: {n0}  |  基準命中率: {base_hit:.4f}")
    print(f"（受讓佔比: {((df['role'] == 'underdog').mean()):.1%}）")
    print()
    print(f"{'政策':<46} {'保留n':>8} {'命中率':>10} {'排除筆數':>10}")
    print("-" * 72)

    rows = []
    for name, mask in policies:
        s = summarize(name, df, mask)
        rows.append(s)
        hit_s = f"{s['hit']:.4f}" if s["n"] > 0 else "  —"
        print(f"{s['policy']:<46} {s['n']:>8} {hit_s:>10} {s['excluded']:>10}")

    print("-" * 72)
    print()
    print("說明:")
    print("  · 「排除」= 模擬該場不採用 spread 建議（不計入保留集）。")
    print("  · 預測機率 proxy：同 evaluate 腳本（win_probability 優先，否則 confidence/100）。")
    print("  · 若命中率上升但保留 n 過小，實務上需取捨曝光量。")
    print()


if __name__ == "__main__":
    main()
