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

# 🕵️‍♂️ 上帝模式：設為 true 可以強制修改歷史預測 (通常用於測試或手動修正)
# 使用方式: export CHEAT_MODE=true (Mac/Linux) 或 set CHEAT_MODE=true (Windows)
CHEAT_MODE = os.getenv("CHEAT_MODE", "false").lower() == "true"

print(f"📂 正在載入 AI 模型... (Cheat Mode: {CHEAT_MODE})")
try:
    model_win = joblib.load('model_win.pkl')
    model_spread = joblib.load('model_spread.pkl')
    model_total = joblib.load('model_total.pkl')
    features_spread = joblib.load('features_spread.pkl')
    features_total = joblib.load('features_total.pkl')
except Exception as e:
    print(f"❌ 模型載入失敗: {e}")
    exit()

RAW_FEATURES = [
    'fieldGoalsPercentage', 'threePointersPercentage', 'freeThrowsPercentage',
    'reboundsTotal', 'assists', 'steals', 'blocks', 'turnovers', 
    'plusMinusPoints', 'pointsInThePaint', 'teamScore'
]

def generate_insight(rec_code, opp_code, is_home_pick, features_df):
    """
    將特徵數據轉換為文字分析報告
    """
    # 定義特徵對應的專業術語
    feature_map = {
        'diff_fieldGoalsPercentage': 'Overall Shooting Efficiency',
        'diff_threePointersPercentage': 'Perimeter Scoring (3PT%)',
        'diff_freeThrowsPercentage': 'Free Throw Reliability',
        'diff_reboundsTotal': 'Rebounding Dominance',
        'diff_assists': 'Ball Movement & Playmaking',
        'diff_steals': 'Defensive Disruptions (Steals)',
        'diff_blocks': 'Rim Protection',
        'diff_turnovers': 'Ball Security (Turnovers)', 
        'diff_plusMinusPoints': 'Recent Point Differential',
        'diff_pointsInThePaint': 'Paint Scoring Presence'
    }

    # 取得第一筆特徵資料 (Series)
    if features_df.empty: return "Analysis unavailable based on current data."
    row = features_df.iloc[0]

    # 找出對推薦隊伍「最有利」的 3 個特徵
    factor_scores = {}
    
    for col, name in feature_map.items():
        if col not in row: continue
        val = row[col]
        
        # 特殊處理：失誤 (Turnovers)，數值越小越好
        if 'turnovers' in col:
            # 如果推薦的是主隊，val (主-客) 為負是好事 => 取負號變成正分
            # 如果推薦的是客隊，val (主-客) 為正是好事 (代表主隊失誤多) => 直接取正值
            # 這裡邏輯簡化：我們想知道這項數據是否支持「推薦隊伍」
            # 推薦主隊: 我們希望 主<客 => val < 0 => score = -val (正分)
            # 推薦客隊: 我們希望 客<主 => val > 0 => score = val (正分)
            score = -val if is_home_pick else val 
        else:
            # 一般數據：越大越好
            # 推薦主隊: 我們希望 主>客 => val > 0 => score = val
            # 推薦客隊: 我們希望 客>主 => val < 0 => score = -val
            score = val if is_home_pick else -val 
            
        factor_scores[name] = score

    # 排序取出前 3 名關鍵因素 (分數越高代表優勢越大)
    top_factors = sorted(factor_scores.items(), key=lambda x: x[1], reverse=True)[:3]
    
    # --- 生成文案 ---
    intro = f"Our AI model identifies a statistical edge for {rec_code} over {opp_code}."
    
    bullet_points = []
    for name, score in top_factors:
        # 根據數值強度給予形容詞
        intensity = "slight"
        if score > 5: intensity = "significant" 
        if score > 10: intensity = "dominant"
        
        bullet_points.append(f"• **{name}**: Shows a {intensity} advantage in recent form.")

    # 總結
    if top_factors:
        summary = f"Comparing the rolling 5-game averages, {rec_code}'s performance in {top_factors[0][0]} is the primary driver for this prediction."
    else:
        summary = "Data analysis suggests a close matchup based on recent performance."

    full_text = f"{intro}\n\n" + "\n".join(bullet_points) + f"\n\n{summary}"
    return full_text

def get_latest_stats():
    print("🔄 從 CSV 讀取球隊近況...")
    try:
        cols = ['teamId', 'gameDateTimeEst'] + RAW_FEATURES
        # 1. 讀取 CSV
        df = pd.read_csv('data/TeamStatistics.csv', usecols=cols, low_memory=False)
        
        # 🔥 同步修復：強制正規化日期 (只取前 10 碼 YYYY-MM-DD)
        # 這樣就能解決帶有時區 (-04:00) 導致解析失敗的問題
        df['gameDateTimeEst'] = df['gameDateTimeEst'].astype(str).str.slice(0, 10)

        # 2. 強壯的日期解析
        df['gameDateTimeEst'] = pd.to_datetime(df['gameDateTimeEst'], utc=True, errors='coerce')
        
        # 3. 移除無效日期 (現在應該會是 0 筆了)
        if df['gameDateTimeEst'].isnull().any():
            print(f"   ⚠️ Warning: 發現 {df['gameDateTimeEst'].isnull().sum()} 筆無效日期，已自動過濾。")
            df = df.dropna(subset=['gameDateTimeEst'])

        df = df.sort_values(['teamId', 'gameDateTimeEst'])
        
        # 4. 滾動平均計算
        df_rolled = df.groupby('teamId', group_keys=False)[RAW_FEATURES].apply(lambda x: x.rolling(5, min_periods=1).mean())
        
        # 把 teamId 加回來
        df_rolled['teamId'] = df['teamId']
        
        last = df_rolled.groupby('teamId').tail(1)
        return {int(r['teamId']): {f"rolling_{c}": r[c] for c in RAW_FEATURES} for _, r in last.iterrows()}
        
    except Exception as e:
        print(f"❌ 讀取 TeamStatistics 失敗: {e}")
        return {}

def prepare_features(h_id, a_id, stats):
    if h_id not in stats or a_id not in stats: return None, None, None
    h, a = stats[h_id], stats[a_id]
    
    row = {'is_home': 1}
    for col in RAW_FEATURES:
        r = f"rolling_{col}"
        row[f"diff_{col}"] = h[r] - a[r]
        row[f"sum_{col}"] = h[r] + a[r]
        
    df = pd.DataFrame([row])
    # 補齊特徵欄位，避免模型報錯
    for c in features_spread: 
        if c not in df.columns: df[c] = 0
    for c in features_total: 
        if c not in df.columns: df[c] = 0
    return df[features_spread], df[features_total], df

def run():
    supabase = get_supabase_client()
    stats = get_latest_stats()
    if not stats: return

    # 設定時間範圍
    now = datetime.utcnow()
    end_date = now + timedelta(days=PREDICT_DAYS)
    
    print(f"📅 抓取賽程範圍: {now.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")

    # 抓取比賽
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
            # ==========================================
            # 🔒 關鍵保護：檢查比賽狀態
            # ==========================================
            finished_statuses = ['STATUS_FINAL', 'STATUS_FINISHED', 'Final', 'STATUS_IN_PROGRESS']
            is_finished = m.get('status') in finished_statuses
            
            if is_finished and not CHEAT_MODE:
                continue

            # --- 以下為預測邏輯 ---
            h_id = int(m['home_team']['nba_team_id'])
            a_id = int(m['away_team']['nba_team_id'])
            
            # 🔥 修改：接收第三個回傳值 raw_df
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
                opp_code = m['away_team']['code'] # 對手
                diff = abs(pred_margin - cutoff)
            else:
                rec_id = m['away_team_id']
                rec_code = m['away_team']['code']
                opp_code = m['home_team']['code'] # 對手
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

            # 🤖 生成 AI 分析文案
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
                "analysis_content": analysis_text, # 🔥 新增欄位
                "created_at": datetime.utcnow().isoformat()
            })
            print(f"   -> {m['away_team']['code']} @ {m['home_team']['code']}: 預測更新 [{rec_code}]")

        except Exception as e:
            print(f"⚠️ Error {m['id']}: {e}")

    # 寫入 (Check-then-Upsert)
    if picks:
        match_ids = [p['match_id'] for p in picks]
        try:
            # 這裡我們只抓 id，用來做 upsert mapping
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