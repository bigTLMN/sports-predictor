import pandas as pd
import joblib
import os
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Tuple
from config import get_supabase_client
from nba_schedule_features import b2b_before_game, load_schedule_for_b2b

# ==========================================
# 設定：只預測未來 1 天 (配合 CI/CD 每日執行)
# ==========================================
PREDICT_DAYS = 1 

# 🕵️‍♂️ 上帝模式
CHEAT_MODE = os.getenv("CHEAT_MODE", "false").lower() == "true"

# 政策 B（靜態門檻）：受讓且 |主隊讓分線|≥門檻時不發佈讓分建議。
# 訓練端只有「實際分差」沒有歷史盤口時，無法用 tune_model 的 MAE 直接等價優化「大受讓蓋盤」；
# 若你相信目前讓分模型 + MARGIN_SHRINK_WEIGHT 已足夠，可關閉此門檻改完全交由模型：
#   SPREAD_POLICY_B_DISABLE=true
# 門檻可調：SPREAD_POLICY_B_MIN_ABS_LINE=12（預設），與 scripts/simulate_spread_policies 政策 B 對齊。
SPREAD_POLICY_B_DISABLE = os.getenv("SPREAD_POLICY_B_DISABLE", "false").lower() == "true"
SPREAD_POLICY_B_MIN_ABS_LINE = float(os.getenv("SPREAD_POLICY_B_MIN_ABS_LINE", "12.0"))

# 推論時將模型 home margin 向盤口隱含 home margin 拉近：pred = (1-w)*raw + w*(-vegas_spread)
MARGIN_SHRINK_WEIGHT = float(os.getenv("MARGIN_SHRINK_WEIGHT", "0.2"))


def _is_recommended_underdog(vegas_spread: float, rec_id: int, home_team_id: int) -> bool:
    """vegas_spread 為主隊視角（負=主隊讓分），判斷推薦隊是否為受讓方。"""
    if rec_id == home_team_id:
        return vegas_spread > 0
    return vegas_spread < 0

print(f"📂 正在載入 V8.0 AI 模型... (Cheat Mode: {CHEAT_MODE})")
if SPREAD_POLICY_B_DISABLE:
    print("   ⚙️ SPREAD_POLICY_B_DISABLE=true — 已關閉「大受讓」靜態門檻，讓分建議完全由模型輸出決定。")
else:
    print(
        f"   ⚙️ 政策 B：受讓且 |line|≥{SPREAD_POLICY_B_MIN_ABS_LINE:g} 時不發佈讓分（設 SPREAD_POLICY_B_DISABLE=true 可關閉）"
    )
try:
    model_win = joblib.load('model_win.pkl')
    model_spread = joblib.load('model_spread.pkl')
    model_total = joblib.load('model_total.pkl')
    features_spread = joblib.load('features_spread.pkl')
    features_total = joblib.load('features_total.pkl')
    
    # 嘗試載入窗口設定，確保與訓練時一致
    try:
        ROLLING_WINDOWS = joblib.load('rolling_config.pkl')
        print(f"   ⚙️ 載入動態窗口設定: {ROLLING_WINDOWS}")
    except:
        ROLLING_WINDOWS = [5, 10, 30] # 預設值
        print(f"   ⚠️ 未找到 rolling_config.pkl，使用預設窗口: {ROLLING_WINDOWS}")

except Exception as e:
    print(f"❌ 模型載入失敗: {e}")
    exit()

# 基礎欄位 (Raw Stats) - 對應訓練時的 BASE_STATS_COLS
BASE_STATS_COLS = [
    'fieldGoalsPercentage', 'threePointersPercentage', 'freeThrowsPercentage',
    'reboundsTotal', 'assists', 'steals', 'blocks', 'turnovers', 
    'plusMinusPoints', 'pointsInThePaint', 'teamScore', 
    'eFG_Percentage', 'TS_Percentage', 'RestDays'
]

# ==========================================
# 🧠 AI 洞察生成核心 (Insight Generator) — 英／繁雙語
# ==========================================
# 特徵欄位需與模型 rolling_5_* 一致；顯示名稱分英文、繁中
_FEATURE_ROWS = [
    ("diff_rolling_5_fieldGoalsPercentage", "Shooting Efficiency (L5)", "投籃效率（近5場）"),
    ("diff_rolling_5_threePointersPercentage", "3-Point Shooting (L5)", "三分投射（近5場）"),
    ("diff_rolling_5_freeThrowsPercentage", "Free Throw Reliability (L5)", "罰球穩定度（近5場）"),
    ("diff_rolling_5_reboundsTotal", "Rebounding Presence (L5)", "籃板影響力（近5場）"),
    ("diff_rolling_5_assists", "Ball Movement (L5)", "傳導與助攻（近5場）"),
    ("diff_rolling_5_steals", "Defensive Pressure (L5)", "防守壓迫（近5場）"),
    ("diff_rolling_5_blocks", "Rim Protection (L5)", "護框阻攻（近5場）"),
    ("diff_rolling_5_turnovers", "Ball Security (L5)", "失誤控制（近5場）"),
    ("diff_rolling_5_plusMinusPoints", "Net Rating Trend (L5)", "正負值趨勢（近5場）"),
    ("diff_rolling_5_pointsInThePaint", "Paint Scoring (L5)", "禁區得分（近5場）"),
    ("diff_rolling_5_win_rate", "Winning Momentum (L5)", "勝率動能（近5場）"),
]


def _score_for_col(row, col: str, is_home_pick: bool) -> Optional[float]:
    if col not in row.index:
        return None
    val = row[col]
    if "turnovers" in col:
        return -val if is_home_pick else val
    return val if is_home_pick else -val


def _intensity_en(score: float) -> str:
    if score > 10:
        return "dominant"
    if score > 5:
        return "significant"
    return "slight"


def _intensity_zh(score: float) -> str:
    if score > 10:
        return "強烈"
    if score > 5:
        return "明顯"
    return "輕微"


def generate_insight_bilingual(rec_code, opp_code, is_home_pick, features_df) -> Tuple[str, str]:
    """
    回傳 (英文全文, 繁中全文)。供 analysis_content / analysis_content_zh 寫入。
    """
    empty_en = "Analysis unavailable based on current data."
    empty_zh = "目前資料不足，無法產出分析。"
    if features_df.empty:
        return empty_en, empty_zh

    row = features_df.iloc[0]
    scored = []
    for col, name_en, name_zh in _FEATURE_ROWS:
        s = _score_for_col(row, col, is_home_pick)
        if s is None:
            continue
        scored.append((col, name_en, name_zh, float(s)))

    top = sorted(scored, key=lambda x: x[3], reverse=True)[:3]

    intro_en = f"Our AI model identifies a statistical edge for {rec_code} over {opp_code}."
    intro_zh = f"AI 模型指出：{rec_code} 相對 {opp_code}，在近期統計指標上較占優勢。"

    bullets_en, bullets_zh = [], []
    for _col, name_en, name_zh, score in top:
        ie, izh = _intensity_en(score), _intensity_zh(score)
        bullets_en.append(f"• **{name_en}**: Shows a {ie} advantage in recent form.")
        bullets_zh.append(f"• **{name_zh}**：近 5 場呈現「{izh}」優勢。")

    if top:
        summary_en = (
            f"Comparing the recent 5-game trends, {rec_code}'s performance in {top[0][1]} "
            f"is a key indicator for this matchup."
        )
        summary_zh = (
            f"綜合近 5 場走勢，{rec_code} 在「{top[0][2]}」上的表現是本場關鍵指標。"
        )
    else:
        summary_en = "Data analysis suggests a close matchup based on recent performance."
        summary_zh = "數據顯示雙方近況接近，賽事可能較為拉鋸。"

    full_en = intro_en + "\n\n" + "\n".join(bullets_en) + "\n\n" + summary_en
    full_zh = intro_zh + "\n\n" + "\n".join(bullets_zh) + "\n\n" + summary_zh
    return full_en, full_zh


def generate_insight(rec_code, opp_code, is_home_pick, features_df):
    """向後相容：僅英文。"""
    en, _zh = generate_insight_bilingual(rec_code, opp_code, is_home_pick, features_df)
    return en

def get_latest_stats():
    print("🔄 [V8.0] 從 CSV 讀取並計算多重窗口統計...")
    try:
        # 1. 讀取 CSV
        req_cols = [
            'teamId', 'gameDateTimeEst', 'win', 'teamScore', 
            'fieldGoalsMade', 'fieldGoalsAttempted', 'threePointersMade', 
            'freeThrowsAttempted',
            'fieldGoalsPercentage', 'threePointersPercentage', 'freeThrowsPercentage',
            'reboundsTotal', 'assists', 'steals', 'blocks', 'turnovers', 
            'plusMinusPoints', 'pointsInThePaint'
        ]
        
        # 使用 lambda 避免欄位不存在報錯
        df = pd.read_csv('data/TeamStatistics.csv', usecols=lambda c: c in req_cols, low_memory=False)
        
        # 2. 日期處理
        df['gameDateTimeEst'] = df['gameDateTimeEst'].astype(str).str.slice(0, 10)
        df['gameDateTimeEst'] = pd.to_datetime(df['gameDateTimeEst'], utc=True, errors='coerce')
        if df['gameDateTimeEst'].isnull().any():
            df = df.dropna(subset=['gameDateTimeEst'])

        # 3. 排序
        df = df.sort_values(['teamId', 'gameDateTimeEst'])
        
        # 4. 特徵工程 (與 Train 保持一致)
        df['threePointersMade'] = df['threePointersMade'].fillna(0)
        df['fieldGoalsAttempted'] = df['fieldGoalsAttempted'].replace(0, np.nan)
        
        df['eFG_Percentage'] = (df['fieldGoalsMade'] + 0.5 * df['threePointersMade']) / df['fieldGoalsAttempted']
        df['TS_Percentage'] = df['teamScore'] / (2 * (df['fieldGoalsAttempted'] + 0.44 * df['freeThrowsAttempted']))
        df['eFG_Percentage'] = df['eFG_Percentage'].fillna(0)
        df['TS_Percentage'] = df['TS_Percentage'].fillna(0)

        df['prev_game_date'] = df.groupby('teamId')['gameDateTimeEst'].shift(1)
        df['RestDays'] = (df['gameDateTimeEst'] - df['prev_game_date']).dt.days
        df['RestDays'] = df['RestDays'].fillna(3).clip(upper=7)
        
        # 數值化勝負 (重要：先移除空值再轉換，避免報錯)
        if df['win'].isnull().any():
            df = df.dropna(subset=['win'])
        df['win_numeric'] = df['win'].astype(int)
        
        # 5. 多重滾動平均計算 (的核心變動)
        cols_to_roll = [c for c in BASE_STATS_COLS if c in df.columns and c != 'RestDays']
        cols_to_roll.append('RestDays')

        rolled_dfs = []
        for w in ROLLING_WINDOWS:
            # 統計數據平均
            r_stats = df.groupby('teamId', group_keys=False)[cols_to_roll].apply(
                lambda x: x.rolling(w, min_periods=1).mean()
            )
            r_stats.columns = [f'rolling_{w}_{c}' for c in r_stats.columns]
            
            # 勝率平均
            r_win = df.groupby('teamId', group_keys=False)['win_numeric'].apply(
                lambda x: x.rolling(w, min_periods=1).mean()
            )
            r_stats[f'rolling_{w}_win_rate'] = r_win
            
            rolled_dfs.append(r_stats)
            
        df = pd.concat([df] + rolled_dfs, axis=1)
        
        # 取出每支球隊的「最後一筆」數據
        last = df.groupby('teamId').tail(1)
        
        # 只保留 rolling_ 開頭的欄位
        keep_cols = [c for c in df.columns if 'rolling_' in c]
        
        result = {}
        for _, r in last.iterrows():
            result[int(r['teamId'])] = {c: r[c] for c in keep_cols}
            
        return result
        
    except Exception as e:
        print(f"❌ 讀取 TeamStatistics 失敗: {e}")
        return {}

def prepare_features(h_id, a_id, stats, b2b_h=0, b2b_a=0):
    if h_id not in stats or a_id not in stats: return None, None, None
    h, a = stats[h_id], stats[a_id]
    
    row = {'is_home': 1}
    
    # 自動計算所有 available 的 diff 和 sum
    for key in h.keys():
        if key in a:
            row[f"diff_{key}"] = h[key] - a[key]
            row[f"sum_{key}"] = h[key] + a[key]

    row["diff_b2b"] = float(b2b_h) - float(b2b_a)
    row["sum_b2b"] = float(b2b_h) + float(b2b_a)
        
    df = pd.DataFrame([row])
    
    # 補齊特徵欄位 (Alignment)
    for c in features_spread: 
        if c not in df.columns: df[c] = 0
    for c in features_total: 
        if c not in df.columns: df[c] = 0
    
    # 回傳：Spread特徵, Total特徵, 原始Diff
    return df[features_spread], df[features_total], df

def run():
    supabase = get_supabase_client()
    stats = get_latest_stats()
    if not stats: return

    try:
        sched_df = load_schedule_for_b2b()
    except Exception as e:
        print(f"⚠️ B2B schedule load failed ({e}); diff_b2b/sum_b2b default to 0.")
        sched_df = pd.DataFrame(columns=["teamId", "gameDateTimeEst"])

    now = datetime.utcnow()
    end_date = now + timedelta(days=PREDICT_DAYS)
    
    print(f"📅 抓取賽程範圍: {now.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")

    matches = supabase.table("matches")\
        .select("*, home_team:teams!matches_home_team_id_fkey(code, nba_team_id), away_team:teams!matches_away_team_id_fkey(code, nba_team_id)")\
        .gte("date", now.isoformat())\
        .lt("date", end_date.isoformat())\
        .order('date')\
        .execute().data

    if not matches:
        print("📭 無比賽。")
        return

    print(f"🤖 準備掃描 {len(matches)} 場比賽...")
    picks = []
    
    for m in matches:
        try:
            # 狀態檢查
            finished_statuses = ['STATUS_FINAL', 'STATUS_FINISHED', 'Final', 'STATUS_IN_PROGRESS']
            is_finished = m.get('status') in finished_statuses
            
            if is_finished and not CHEAT_MODE:
                continue

            h_id = int(m['home_team']['nba_team_id'])
            a_id = int(m['away_team']['nba_team_id'])

            match_time = pd.to_datetime(m["date"], utc=True, errors="coerce")
            if pd.isna(match_time):
                match_time = pd.Timestamp(datetime.utcnow(), tz="UTC")
            bh = b2b_before_game(sched_df, h_id, match_time)
            ba = b2b_before_game(sched_df, a_id, match_time)

            X_spr, X_tot, raw_df = prepare_features(h_id, a_id, stats, bh, ba)
            if X_spr is None: continue

            # AI 預測（讓分模型輸出為 home 視角淨勝分）
            pred_margin = float(model_spread.predict(X_spr)[0])
            pred_total = float(model_total.predict(X_tot)[0])

            # 莊家盤口
            raw_vegas_spread = m.get("vegas_spread")
            vegas_total = m.get("vegas_total")

            # 盤口 shrinkage：僅在有有效讓分時拉近模型與市場
            if (
                raw_vegas_spread is not None
                and MARGIN_SHRINK_WEIGHT > 0.0
                and abs(float(raw_vegas_spread)) > 1e-6
            ):
                market_home_margin = -float(raw_vegas_spread)
                w = MARGIN_SHRINK_WEIGHT
                pred_margin = (1.0 - w) * pred_margin + w * market_home_margin

            vegas_spread = float(raw_vegas_spread) if raw_vegas_spread is not None else 0.0
            if vegas_total is None:
                vegas_total = 225.0

            # 邏輯核心
            cutoff = vegas_spread * -1
            if pred_margin > cutoff: 
                rec_id = m['home_team_id']
                rec_code = m['home_team']['code']
                opp_code = m['away_team']['code']
                diff = abs(pred_margin - cutoff)
            else:
                rec_id = m['away_team_id']
                rec_code = m['away_team']['code']
                opp_code = m['home_team']['code']
                diff = abs(pred_margin - cutoff)

            conf = min(50 + int(diff * 4), 95)
            ou_pick = "OVER" if pred_total > vegas_total else "UNDER"
            ou_conf = min(50 + int(abs(pred_total - vegas_total) * 3), 90)

            vs = float(vegas_spread)
            withhold_spread = (
                not SPREAD_POLICY_B_DISABLE
                and _is_recommended_underdog(vs, rec_id, m["home_team_id"])
                and abs(vs) >= SPREAD_POLICY_B_MIN_ABS_LINE
            )

            is_rec_home = (rec_id == m['home_team_id'])
            my_proj_margin = pred_margin if is_rec_home else -pred_margin

            # 生成 AI 分析文案（英／繁）
            analysis_text_en, analysis_text_zh = generate_insight_bilingual(
                rec_code,
                opp_code,
                is_rec_home,
                raw_df,
            )

            if my_proj_margin > 0:
                logic_str_en = f"AI projects {rec_code} to win by {abs(my_proj_margin):.1f} pts"
                logic_str_zh = f"AI 預測 {rec_code} 贏 {abs(my_proj_margin):.1f} 分"
            else:
                logic_str_en = f"AI projects {rec_code} to lose by {abs(my_proj_margin):.1f} pts"
                logic_str_zh = f"AI 預測 {rec_code} 輸 {abs(my_proj_margin):.1f} 分"

            if withhold_spread:
                line_info_val = ""
                spread_logic_out_en = "Spread pick withheld (large underdog filter)."
                spread_logic_out_zh = "因大受讓政策，本場不發佈讓分建議。"
                confidence_out = ou_conf
                print(
                    f"   -> {m['away_team']['code']} @ {m['home_team']['code']}: "
                    f"政策B 不發佈讓分 [{rec_code}] |line|={abs(vs):.1f}，仍更新 O/U"
                )
            else:
                line_info_val = str(vegas_spread)
                spread_logic_out_en = logic_str_en
                spread_logic_out_zh = logic_str_zh
                confidence_out = conf

            picks.append({
                "match_id": m['id'],
                "recommended_team_id": rec_id,
                "confidence_score": confidence_out,
                "spread_logic": spread_logic_out_en,
                "spread_logic_zh": spread_logic_out_zh,
                "line_info": line_info_val,
                "ou_pick": ou_pick,
                "ou_line": float(vegas_total),
                "ou_confidence": ou_conf,
                "analysis_content": analysis_text_en,
                "analysis_content_zh": analysis_text_zh,
                # 供前端顯示：推薦隊視角淨勝分（正=預測贏幾分，負=預測輸幾分）；模型預測總分
                "predicted_margin": round(float(my_proj_margin), 2),
                "predicted_total": round(float(pred_total), 2),
                "created_at": datetime.utcnow().isoformat()
            })
            if not withhold_spread:
                print(f"   -> {m['away_team']['code']} @ {m['home_team']['code']}: 預測更新 [{rec_code}]")

        except Exception as e:
            print(f"⚠️ Error {m['id']}: {e}")

    # 寫入
    if picks:
        match_ids = [p['match_id'] for p in picks]
        try:
            existing = supabase.table("aggregated_picks").select("id, match_id").in_("match_id", match_ids).execute().data
            existing_map = {item['match_id']: item['id'] for item in existing}
            
            for p in picks:
                if p['match_id'] in existing_map:
                    p['id'] = existing_map[p['match_id']]
            
            supabase.table("aggregated_picks").upsert(picks).execute()
            print(f"✅ 完成！已更新 {len(picks)} 筆未開賽預測。")
        except Exception as e:
            print(f"❌ 寫入失敗: {e}")
    else:
        print("✅ 無需更新 (沒有未開賽的比賽)。")

if __name__ == "__main__":
    run()