"""
從 Supabase 匯出的 aggregated_picks CSV 做 spread / total 回測評量。

使用方式:
  python scripts/evaluate_aggregated_picks.py --picks path/to/aggregated_picks_rows.csv
  python scripts/evaluate_aggregated_picks.py --picks ... --days 90
  python scripts/evaluate_aggregated_picks.py --picks ... --matches path/to/matches_rows.csv

若需分析「受讓方 / 大讓分」與實際輸分分佈，請另匯出 matches 並以 --matches 指定，欄位至少:
  match_id, home_team_id, away_team_id, home_score, away_score

範例 SQL (Supabase):
  select m.id as match_id, m.home_team_id, m.away_team_id, m.home_score, m.away_score
  from matches m
  where m.status in ('STATUS_FINAL','STATUS_FINISHED','Final');
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def _clip_prob(p: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    return np.clip(p.astype(float), eps, 1.0 - eps)


def log_loss_binary(y: np.ndarray, p: np.ndarray) -> float:
    """平均 log loss，y in {0,1}, p 為 P(y=1)。"""
    p = _clip_prob(p)
    y = y.astype(float)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def brier_score(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean((p.astype(float) - y.astype(float)) ** 2))


def pick_spread_probability(row: pd.Series) -> float | None:
    """勝率用於『推薦隊伍過盤』的 proxy：優先 win_probability，否則 confidence_score/100。"""
    if pd.notna(row.get("win_probability")):
        return float(row["win_probability"])
    if pd.notna(row.get("confidence_score")):
        return float(row["confidence_score"]) / 100.0
    return None


def load_picks(path: Path, days: int | None) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
    if days is not None:
        end = df["created_at"].max()
        df = df[df["created_at"] >= end - pd.Timedelta(days=days)].copy()
    return df


def role_favorite_underdog(row: pd.Series) -> str | None:
    """
    依主隊讓分線與推薦主/客判斷推薦隊是『讓分方』或『受讓方』。
    與 scrape_odds / grade_picks 一致：line_info 為主隊視角（負=主隊讓分）。
    """
    try:
        line = float(row["line_info"])
    except (TypeError, ValueError):
        return None
    home_pick = row["recommended_team_id"] == row["home_team_id"]
    if home_pick:
        return "favorite" if line < 0 else "underdog"
    return "underdog" if line < 0 else "favorite"


def normalize_matches_columns(m: pd.DataFrame) -> pd.DataFrame:
    """Supabase 匯出常用 `id` 作場次主鍵，與 picks.match_id 對應。"""
    m = m.copy()
    if "match_id" not in m.columns and "id" in m.columns:
        m = m.rename(columns={"id": "match_id"})
    return m


def filter_finished_matches(m: pd.DataFrame) -> pd.DataFrame:
    """排除未開打占位比數 0:0，避免輸分分析錯誤。"""
    if m.empty:
        return m
    out = m.copy()
    if "status" in out.columns:
        st = out["status"].astype(str)
        fin = st.str.contains("FINISH|Final", case=False, na=False)
        out = out[fin]
    if "home_score" in out.columns and "away_score" in out.columns:
        out = out[out["home_score"].notna() & out["away_score"].notna()]
        out = out[~((out["home_score"] == 0) & (out["away_score"] == 0))]
    return out


def game_margin_for_recommended(row: pd.Series) -> float | None:
    """從推薦隊視角的分差 (正=該隊贏幾分)。"""
    hs, aw = row.get("home_score"), row.get("away_score")
    if pd.isna(hs) or pd.isna(aw):
        return None
    hs, aw = float(hs), float(aw)
    if row["recommended_team_id"] == row["home_team_id"]:
        return hs - aw
    return aw - hs


def run_report(
    picks: pd.DataFrame,
    matches: pd.DataFrame | None,
    prob_source_note: str,
) -> None:
    # ---------- Spread ----------
    sp = picks[picks["spread_outcome"].isin(["WIN", "LOSS"])].copy()
    if sp.empty:
        print("沒有已結算 spread (WIN/LOSS) 的資料。")
    else:
        y_sp = (sp["spread_outcome"] == "WIN").astype(int).values
        p_list = []
        for _, r in sp.iterrows():
            pr = pick_spread_probability(r)
            p_list.append(pr)
        p_sp = np.array([x if x is not None else np.nan for x in p_list], dtype=float)
        mask = ~np.isnan(p_sp)
        n_all = len(sp)
        hit = float(y_sp.mean())
        print("=== Spread（讓分盤）===")
        print(f"樣本數: {n_all}  命中率: {hit:.4f}")
        if mask.sum():
            print(
                f"  Log loss (有機率欄位之列, n={mask.sum()}): {log_loss_binary(y_sp[mask], p_sp[mask]):.4f}"
            )
            print(f"  Brier score (同上): {brier_score(y_sp[mask], p_sp[mask]):.4f}")
            print(f"  機率來源: {prob_source_note}")

        # 校準表：依預測機率分箱
        if mask.sum() >= 10:
            cal = sp.loc[mask].copy()
            cal["y"] = (cal["spread_outcome"] == "WIN").astype(int)
            cal["p"] = p_sp[mask]
            try:
                cal["bin"] = pd.qcut(cal["p"], q=min(10, cal["p"].nunique()), duplicates="drop")
            except ValueError:
                cal["bin"] = pd.cut(cal["p"], bins=10, duplicates="drop")
            grp = cal.groupby("bin", observed=True)
            print("  校準（分箱｜筆數｜平均預測機率｜實際過盤率）:")
            for name, g in grp:
                print(
                    f"    {name}  |  n={len(g):3d}  pred={g['p'].mean():.3f}  actual={g['y'].mean():.3f}"
                )

        # 信心區間分層（用 confidence_score）
        if sp["confidence_score"].notna().any():
            sp2 = sp[sp["confidence_score"].notna()].copy()
            sp2["y"] = (sp2["spread_outcome"] == "WIN").astype(int)
            sp2["cb"] = pd.cut(
                sp2["confidence_score"].astype(float),
                bins=[0, 55, 65, 75, 85, 100],
                include_lowest=True,
            )
            print("  依 confidence_score 分層命中率:")
            for name, g in sp2.groupby("cb", observed=True):
                print(f"    {name}  n={len(g):3d}  hit={g['y'].mean():.3f}")

        # |line| 分桶
        try:
            sp["abs_line"] = sp["line_info"].astype(float).abs()
            sp["line_bucket"] = pd.cut(
                sp["abs_line"],
                bins=[0, 3, 7, 10, 100],
                labels=["0-3", "3.5-7", "7.5-10", "10+"],
            )
            sp["y"] = (sp["spread_outcome"] == "WIN").astype(int)
            print("  依 |讓分線| 分層命中率:")
            for name, g in sp.groupby("line_bucket", observed=True):
                if len(g) == 0:
                    continue
                print(f"    |line| {name}  n={len(g):3d}  hit={g['y'].mean():.3f}")
        except Exception as e:
            print(f"  (|line| 分層略過: {e})")

    # ---------- Total ----------
    tot = picks[picks["total_outcome"].isin(["WIN", "LOSS"])].copy()
    if not tot.empty:
        y_t = (tot["total_outcome"] == "WIN").astype(int).values
        p_t = []
        for _, r in tot.iterrows():
            if pd.notna(r.get("ou_confidence")):
                p_t.append(float(r["ou_confidence"]) / 100.0)
            else:
                p_t.append(np.nan)
        p_t = np.array(p_t, dtype=float)
        mask_t = ~np.isnan(p_t)
        print("\n=== Total（大小分）===")
        print(f"樣本數: {len(tot)}  命中率: {y_t.mean():.4f}")
        if mask_t.sum():
            print(
                f"  Log loss (ou_confidence 作機率 proxy, n={mask_t.sum()}): "
                f"{log_loss_binary(y_t[mask_t], p_t[mask_t]):.4f}"
            )
            print(f"  Brier: {brier_score(y_t[mask_t], p_t[mask_t]):.4f}")

    # ---------- Optional: matches merge ----------
    if matches is not None and not matches.empty and sp is not None and len(sp):
        m = normalize_matches_columns(matches)
        need = {"match_id", "home_team_id", "away_team_id", "home_score", "away_score"}
        if not need.issubset(set(m.columns)):
            print(
                f"\n[matches] 缺少欄位，需要 match_id（或 id）與: "
                f"home_team_id, away_team_id, home_score, away_score — 已略過受讓/輸分分析。"
            )
            return
        cols = list(need)
        if "status" in m.columns:
            cols.append("status")
        m = m[cols].drop_duplicates(subset=["match_id"])
        m = filter_finished_matches(m)
        merged = sp.merge(m, on="match_id", how="inner")
        if merged.empty:
            print("\n[matches] 與 picks 無法 join（或無已完賽比數），略過受讓/輸分分析。")
            return
        print(f"\n[matches] 與 spread 已結算合併筆數: {len(merged)} / {len(sp)}")

        merged["role"] = merged.apply(role_favorite_underdog, axis=1)
        merged["gm_rec"] = merged.apply(game_margin_for_recommended, axis=1)

        print("\n=== Spread + matches：受讓 / 讓分方 命中率 ===")
        for role in ["favorite", "underdog"]:
            sub = merged[merged["role"] == role]
            if sub.empty:
                continue
            hit_r = (sub["spread_outcome"] == "WIN").mean()
            print(f"  {role}: n={len(sub)}  hit={hit_r:.3f}")

        try:
            merged["abs_line"] = merged["line_info"].astype(float).abs()
            ud = merged[merged["role"] == "underdog"]
            big = ud[ud["abs_line"] >= 12.0]
            if len(big):
                h = (big["spread_outcome"] == "WIN").mean()
                print(f"\n  受讓且 |line|>=12: n={len(big)}  hit={h:.3f}")
            if len(ud):
                print("\n=== 受讓方 LOSS 時，實際『推薦隊』輸幾分（絕對值）===")
                lost = ud[(ud["spread_outcome"] == "LOSS") & ud["gm_rec"].notna()]
                if len(lost):
                    # 輸球時 gm_rec 為負，顯示輸分絕對值
                    margins = (-lost["gm_rec"]).clip(lower=0)
                    print(f"  樣本數: {len(lost)}  平均輸分: {margins.mean():.2f}  中位數: {margins.median():.2f}")
                    print(f"  分佈 (輸 20-30 分): {((margins >= 20) & (margins <= 30)).sum()} 筆")
        except Exception as e:
            print(f"  (受讓細部分析略過: {e})")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="aggregated_picks 回測評量")
    parser.add_argument("--picks", type=Path, required=True, help="aggregated_picks_rows.csv 路徑")
    parser.add_argument("--days", type=int, default=None, help="僅保留最近 N 天（預設：不篩，用檔案內全部）")
    parser.add_argument(
        "--matches",
        type=Path,
        default=None,
        help="可選：matches 匯出 CSV（match_id 或 id、home_team_id、away_team_id、home_score、away_score；可有 status）",
    )
    args = parser.parse_args()

    if not args.picks.is_file():
        print(f"找不到檔案: {args.picks}", file=sys.stderr)
        sys.exit(1)

    picks = load_picks(args.picks, args.days)
    matches = None
    if args.matches:
        if not args.matches.is_file():
            print(f"找不到 matches 檔案: {args.matches}", file=sys.stderr)
            sys.exit(1)
        matches = pd.read_csv(args.matches, low_memory=False)

    has_wp = picks["win_probability"].notna().any()
    prob_note = (
        "優先 win_probability，缺則 confidence_score/100"
        if has_wp
        else "confidence_score/100（無 win_probability）"
    )

    print(f"資料筆數（篩選後）: {len(picks)}")
    if args.days:
        print(f"篩選: 最近 {args.days} 天（以 created_at 最晚日為基準）")
    run_report(picks, matches, prob_note)


if __name__ == "__main__":
    main()
