import pandas as pd
import joblib
from datetime import datetime, timedelta
from config import get_supabase_client

# ==========================================
# 設定：只預測未來 1 天 (配合 CI/CD 每日執行)
# ==========================================
PREDICT_DAYS = 1 

print("📂 正在載入 AI 模型...")
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
        df = pd.read_csv('data/TeamStatistics.csv', usecols=cols, low_memory=False)
        
        # 🔥 修改處：加上 format='mixed' 以解決日期解析錯誤
        df['gameDateTimeEst'] = pd.to_datetime(df['gameDateTimeEst'], format='mixed', utc=True)
        
        df = df.sort_values(['teamId', 'gameDateTimeEst'])
        
        df_rolled = df.groupby('teamId')[RAW_FEATURES].apply(lambda x: x.rolling(5, min_periods=1).mean())
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

    # 抓取比賽
    matches = supabase.table("matches")\
        .select("*, home_team:teams!matches_home_team_id_fkey(code, nba_team_id), away_team:teams!matches_away_team_id_fkey(code, nba_team_id)")\
        .eq("status", "STATUS_SCHEDULED")\
        .gte("date", now.isoformat())\
        .lt("date", end_date.isoformat())\
        .order('date')\
        .execute().data

    if not matches:
        print("📭 無未開打比賽。")
        return

    print(f"🤖 準備預測 {len(matches)} 場比賽...")
    picks = []
    
    for m in matches:
        try:
            h_id = int(m['home_team']['nba_team_id'])
            a_id = int(m['away_team']['nba_team_id'])
            
            X_spr, X_tot = prepare_features(h_id, a_id, stats)
            if X_spr is None: continue

            # AI 預測
            pred_margin = float(model_spread.predict(X_spr)[0]) 
            pred_total = float(model_total.predict(X_tot)[0])

            # 莊家盤口 (如果沒有，就用 AI 預測模擬一個 PK 盤)
            vegas_spread = m.get('vegas_spread')
            vegas_total = m.get('vegas_total')
            
            if vegas_spread is None: vegas_spread = 0.0
            if vegas_total is None: vegas_total = 225.0

            # --- 邏輯核心：AI vs Vegas ---
            cutoff = vegas_spread * -1
            
            if pred_margin > cutoff: 
                # AI 覺得主隊表現比莊家預期好 -> 買主隊
                rec_id = m['home_team_id']
                rec_code = m['home_team']['code']
                diff = abs(pred_margin - cutoff)
            else:
                # 買客隊
                rec_id = m['away_team_id']
                rec_code = m['away_team']['code']
                diff = abs(pred_margin - cutoff)

            # 信心度計算 (基礎 50%，每差 1 分加 4%)
            conf = min(50 + int(diff * 4), 95)

            # 大小分推薦
            ou_pick = "OVER" if pred_total > vegas_total else "UNDER"
            ou_conf = min(50 + int(abs(pred_total - vegas_total) * 3), 90)

            # --- 修正邏輯：準確描述 AI 預測是「贏幾分」還是「輸幾分」 ---
            is_rec_home = (rec_id == m['home_team_id'])
            
            if is_rec_home:
                my_proj_margin = pred_margin
            else:
                my_proj_margin = -pred_margin # 客隊視角要取負號

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
            print(f"   -> {m['away_team']['code']} @ {m['home_team']['code']}: 莊家[{vegas_spread}] vs AI[{pred_margin:.1f}] -> 買 {rec_code}")

        except Exception as e:
            print(f"⚠️ Error {m['id']}: {e}")

    # 寫入 (Check-then-Upsert)
    if picks:
        match_ids = [p['match_id'] for p in picks]
        try:
            # 查詢既有 ID 以便更新
            existing = supabase.table("aggregated_picks").select("id, match_id").in_("match_id", match_ids).execute().data
            existing_map = {item['match_id']: item['id'] for item in existing}
            
            for p in picks:
                if p['match_id'] in existing_map:
                    p['id'] = existing_map[p['match_id']]
            
            supabase.table("aggregated_picks").upsert(picks).execute()
            print(f"✅ 完成！已寫入 {len(picks)} 筆最佳推薦。")
        except Exception as e:
            print(f"❌ 寫入失敗: {e}")
    else:
        print("✅ 無需更新。")

if __name__ == "__main__":
    run()