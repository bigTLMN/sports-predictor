import pandas as pd
import joblib
import os
import numpy as np
from datetime import datetime, timedelta
from config import get_supabase_client

# ==========================================
# 設定：只預測未來 1 天 (配合 CI/CD 每日執行)
# ==========================================
PREDICT_DAYS = 1 

# 🕵️‍♂️ 上帝模式
CHEAT_MODE = os.getenv("CHEAT_MODE", "false").lower() == "true"

print(f"📂 正在載入 V8.0 AI 模型... (Cheat Mode: {CHEAT_MODE})")
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
# 🧠 AI 洞察生成核心 (Insight Generator)
# ==========================================
def generate_insight(rec_code, opp_code, is_home_pick, features_df):
    """
    將特徵數據轉換為文字分析報告
    目前鎖定 'Rolling 5' (近況) 作為主要解釋依據
    """
    # 定義特徵對應的專業術語 (針對近 5 場)
    # 🔥 關鍵修正：這裡的 key 必須對應新模型的特徵名稱 (rolling_5_...)
    feature_map = {
        'diff_rolling_5_fieldGoalsPercentage': 'Shooting Efficiency (L5)',
        'diff_rolling_5_threePointersPercentage': '3-Point Shooting (L5)',
        'diff_rolling_5_freeThrowsPercentage': 'Free Throw Reliability (L5)',
        'diff_rolling_5_reboundsTotal': 'Rebounding Presence (L5)',
        'diff_rolling_5_assists': 'Ball Movement (L5)',
        'diff_rolling_5_steals': 'Defensive Pressure (L5)',
        'diff_rolling_5_blocks': 'Rim Protection (L5)',
        'diff_rolling_5_turnovers': 'Ball Security (L5)', 
        'diff_rolling_5_plusMinusPoints': 'Net Rating Trend (L5)',
        'diff_rolling_5_pointsInThePaint': 'Paint Scoring (L5)',
        'diff_rolling_5_win_rate': 'Winning Momentum (L5)'
    }

    if features_df.empty: return "Analysis unavailable based on current data."
    row = features_df.iloc[0]

    factor_scores = {}
    
    for col, name in feature_map.items():
        if col not in row: continue
        val = row[col]
        
        # 特殊處理：失誤 (Turnovers)，數值越小越好
        if 'turnovers' in col:
            score = -val if is_home_pick else val 
        else:
            score = val if is_home_pick else -val 
            
        factor_scores[name] = score

    # 排序取出前 3 名關鍵因素
    top_factors = sorted(factor_scores.items(), key=lambda x: x[1], reverse=True)[:3]
    
    # --- 生成文案 ---
    intro = f"Our AI model identifies a statistical edge for {rec_code} over {opp_code}."
    
    bullet_points = []
    for name, score in top_factors:
        intensity = "slight"
        if score > 5: intensity = "significant" 
        if score > 10: intensity = "dominant"
        
        bullet_points.append(f"• **{name}**: Shows a {intensity} advantage in recent form.")

    if top_factors:
        summary = f"Comparing the recent 5-game trends, {rec_code}'s performance in {top_factors[0][0]} is a key indicator for this matchup."
    else:
        summary = "Data analysis suggests a close matchup based on recent performance."

    full_text = f"{intro}\n\n" + "\n".join(bullet_points) + f"\n\n{summary}"
    return full_text

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

def prepare_features(h_id, a_id, stats):
    if h_id not in stats or a_id not in stats: return None, None, None
    h, a = stats[h_id], stats[a_id]
    
    row = {'is_home': 1}
    
    # 自動計算所有 available 的 diff 和 sum
    for key in h.keys():
        if key in a:
            row[f"diff_{key}"] = h[key] - a[key]
            row[f"sum_{key}"] = h[key] + a[key]
        
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
            
            X_spr, X_tot, raw_df = prepare_features(h_id, a_id, stats)
            if X_spr is None: continue

            # AI 預測
            pred_margin = float(model_spread.predict(X_spr)[0]) 
            pred_total = float(model_total.predict(X_tot)[0])

            # 莊家盤口
            vegas_spread = m.get('vegas_spread')
            vegas_total = m.get('vegas_total')
            
            if vegas_spread is None: vegas_spread = 0.0
            if vegas_total is None: vegas_total = 225.0

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

            is_rec_home = (rec_id == m['home_team_id'])
            my_proj_margin = pred_margin if is_rec_home else -pred_margin 
            
            if my_proj_margin > 0:
                logic_str = f"AI projects {rec_code} to win by {abs(my_proj_margin):.1f} pts"
            else:
                logic_str = f"AI projects {rec_code} to lose by {abs(my_proj_margin):.1f} pts"

            # 生成 AI 分析文案
            analysis_text = generate_insight(
                rec_code, 
                opp_code,
                is_rec_home,
                raw_df
            )

            picks.append({
                "match_id": m['id'],
                "recommended_team_id": rec_id,
                "confidence_score": conf,
                "spread_logic": logic_str,
                "line_info": str(vegas_spread), 
                "ou_pick": ou_pick,
                "ou_line": float(vegas_total),
                "ou_confidence": ou_conf,
                "analysis_content": analysis_text,
                "created_at": datetime.utcnow().isoformat()
            })
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