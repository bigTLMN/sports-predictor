import pandas as pd
import joblib
import os
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

def get_latest_stats():
    print("🔄 從 CSV 讀取球隊近況...")
    try:
        cols = ['teamId', 'gameDateTimeEst'] + RAW_FEATURES
        # 1. 讀取 CSV
        df = pd.read_csv('data/TeamStatistics.csv', usecols=cols, low_memory=False)
        
        # 🔥🔥🔥 關鍵修正：移除 format='mixed'，加入 errors='coerce' 🔥🔥🔥
        # 這樣如果遇到無法解析的日期，它會變成 NaT 而不會報錯 crash
        df['gameDateTimeEst'] = pd.to_datetime(df['gameDateTimeEst'], utc=True, errors='coerce')
        
        # 移除壞掉的日期行
        if df['gameDateTimeEst'].isnull().any():
            print(f"   ⚠️ 發現 {df['gameDateTimeEst'].isnull().sum()} 筆無效日期，已自動過濾。")
            df = df.dropna(subset=['gameDateTimeEst'])

        df = df.sort_values(['teamId', 'gameDateTimeEst'])
        
        # group_keys=False 避免索引衝突
        df_rolled = df.groupby('teamId', group_keys=False)[RAW_FEATURES].apply(lambda x: x.rolling(5, min_periods=1).mean())
        df_rolled['teamId'] = df['teamId']
        
        last = df_rolled.groupby('teamId').tail(1)
        return {int(r['teamId']): {f"rolling_{c}": r[c] for c in RAW_FEATURES} for _, r in last.iterrows()}
        
    except Exception as e:
        print(f"❌ 讀取 TeamStatistics 失敗: {e}")
        return {}

def prepare_features(h_id, a_id, stats):
    if h_id not in stats or a_id not in stats: return None, None
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
    return df[features_spread], df[features_total]

def run():
    supabase = get_supabase_client()
    stats = get_latest_stats()
    if not stats: return

    # 設定時間範圍
    now = datetime.utcnow()
    end_date = now + timedelta(days=PREDICT_DAYS)
    
    print(f"📅 抓取賽程範圍: {now.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")

    # 抓取比賽 (這裡不限狀態，由下方迴圈決定是否更新)
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
            # 定義哪些狀態算是「完賽」
            finished_statuses = ['STATUS_FINAL', 'STATUS_FINISHED', 'Final', 'STATUS_IN_PROGRESS']
            is_finished = m.get('status') in finished_statuses
            
            # 如果比賽已經開始或結束，且沒有開上帝模式 -> 跳過預測 (保護已產生的結果)
            if is_finished and not CHEAT_MODE:
                # 只有在 console 印出 log，但不加入更新列表
                # print(f"   🔒 跳過已開打/完賽: {m['away_team']['code']} @ {m['home_team']['code']} (ID: {m['id']})")
                continue

            # --- 以下為預測邏輯 ---
            h_id = int(m['home_team']['nba_team_id'])
            a_id = int(m['away_team']['nba_team_id'])
            
            X_spr, X_tot = prepare_features(h_id, a_id, stats)
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
                diff = abs(pred_margin - cutoff)
            else:
                rec_id = m['away_team_id']
                rec_code = m['away_team']['code']
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

            picks.append({
                "match_id": m['id'],
                "recommended_team_id": rec_id,
                "confidence_score": conf,
                "spread_logic": logic_str,
                "line_info": str(vegas_spread), 
                "ou_pick": ou_pick,
                "ou_line": float(vegas_total),
                "ou_confidence": ou_conf,
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