import pandas as pd
from config import get_supabase_client
from datetime import datetime, timedelta
import pytz

def import_strict_lite():
    supabase = get_supabase_client()
    print("🧹 [Reset Lite] 正在匯入賽程 (輕量版: 只抓近 3 年)...")

    try:
        df = pd.read_csv('data/Games.csv', low_memory=False)
        print(f"📂 原始 CSV 共有 {len(df)} 筆資料")
    except Exception as e:
        print(f"❌ 讀取失敗: {e}")
        return

    # 1. 時間處理
    df['gameDateTimeEst'] = pd.to_datetime(df['gameDateTimeEst'], utc=True)
    
    # ==========================================
    # 🔥 關鍵修改：只保留最近 3 年的數據
    # ==========================================
    # 設定截斷點：從今天往前推 3 年 (約 1000 天)
    # 這樣大約會涵蓋 2023-2026 的賽季
    cutoff_date = datetime.now(pytz.utc) - timedelta(days=365 * 3)
    
    # 進行過濾
    df_recent = df[df['gameDateTimeEst'] >= cutoff_date]
    print(f"📉 過濾後剩餘 {len(df_recent)} 筆 (僅保留 {cutoff_date.date()} 之後的比賽)")
    
    matches_to_insert = []
    
    # 預先快取球隊 ID (加速用)
    print("🔄 快取球隊 ID map...")
    teams_data = supabase.table('teams').select('id, nba_team_id').execute().data
    nba_id_map = {t['nba_team_id']: t['id'] for t in teams_data if t['nba_team_id']}

    print("🚀 開始寫入 Supabase...")

    for index, row in df_recent.iterrows():
        try:
            h_nba_id = int(row['hometeamId'])
            a_nba_id = int(row['awayteamId'])
            
            if h_nba_id not in nba_id_map or a_nba_id not in nba_id_map:
                continue 

            # 判斷狀態
            if pd.notna(row['homeScore']) and pd.notna(row['awayScore']):
                status = "STATUS_FINISHED"
                h_score = int(row['homeScore'])
                a_score = int(row['awayScore'])
            else:
                status = "STATUS_SCHEDULED"
                h_score = None
                a_score = None

            matches_to_insert.append({
                "date": row['gameDateTimeEst'].isoformat(),
                "home_team_id": nba_id_map[h_nba_id],
                "away_team_id": nba_id_map[a_nba_id],
                "status": status,
                "home_score": h_score,
                "away_score": a_score
            })

            if len(matches_to_insert) >= 500:
                supabase.table('matches').insert(matches_to_insert).execute()
                matches_to_insert = []
                print(f"   -> 已處理... (剩餘 {len(df_recent) - index} 筆)")

        except Exception as e:
            print(f"⚠️ Row {index} Error: {e}")

    if matches_to_insert:
        supabase.table('matches').insert(matches_to_insert).execute()
    
    print("✅ 輕量化匯入完成！資料庫現在很乾淨。")

if __name__ == "__main__":
    import_strict_lite()