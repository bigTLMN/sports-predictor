import pandas as pd
import requests
import os
import time
from datetime import datetime, timedelta

# ==========================================
# 嚴格定義 CSV 欄位順序 (必須與歷史資料完全一致)
# 這些是 train_model.py 需要的欄位
# ==========================================
CSV_HEADERS = [
    'gameId', 'teamId', 'gameDateTimeEst', 'home', 'win', 
    'teamScore', 'opponentScore', 
    'fieldGoalsPercentage', 'threePointersPercentage', 'freeThrowsPercentage',
    'reboundsTotal', 'assists', 'steals', 'blocks', 'turnovers', 
    'plusMinusPoints', 'pointsInThePaint'
]

# ESPN API
ESPN_BASE = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba"

def fetch_daily_stats(date_str):
    """
    抓取指定日期的比賽數據，並格式化為 Training Data 格式
    date_str: YYYYMMDD
    """
    url = f"{ESPN_BASE}/scoreboard?dates={date_str}&limit=100"
    print(f"🕵️‍♂️ [Stats] Fetching data for {date_str}...")
    
    try:
        data = requests.get(url, timeout=10).json()
    except Exception as e:
        print(f"❌ API Error: {e}")
        return []

    new_rows = []
    
    for event in data.get('events', []):
        try:
            game_id = event['id']
            date_est = event['date'] # UTC string
            competitors = event['competitions'][0]['competitors']
            
            # 取得兩隊物件
            home_comp = next(c for c in competitors if c['homeAway'] == 'home')
            away_comp = next(c for c in competitors if c['homeAway'] == 'away')
            
            # 確保比賽已結束且有分數
            if not (event['status']['type']['completed']):
                continue 

            # 兩隊都要抓 (因為 CSV 是一隊一行)
            for team, opp in [(home_comp, away_comp), (away_comp, home_comp)]:
                team_id = team['team']['id']
                
                # 呼叫 Summary API 取得詳細 Boxscore
                stats = get_boxscore_stats(game_id, team_id)
                
                if not stats:
                    print(f"   ⚠️ No detailed stats for Game {game_id} Team {team['team']['abbreviation']}")
                    continue

                # 組裝資料列
                row = {
                    'gameId': game_id,
                    'teamId': team_id, 
                    'gameDateTimeEst': date_est,
                    'home': 1 if team['homeAway'] == 'home' else 0,
                    'win': 1 if team.get('winner') else 0, # ESPN winner flag
                    'teamScore': int(team['score']),
                    'opponentScore': int(opp['score']),
                    
                    # 詳細數據 (若 API 缺值則補 0)
                    'fieldGoalsPercentage': stats.get('fieldGoalsPercentage', 0),
                    'threePointersPercentage': stats.get('threePointFieldGoalsPercentage', 0),
                    'freeThrowsPercentage': stats.get('freeThrowsPercentage', 0),
                    'reboundsTotal': stats.get('totalRebounds', 0),
                    'assists': stats.get('assists', 0),
                    'steals': stats.get('steals', 0),
                    'blocks': stats.get('blocks', 0),
                    'turnovers': stats.get('turnovers', 0),
                    'plusMinusPoints': 0, # ESPN summary 通常不直接給 +/-，這裡暫時補 0 (對勝負預測影響較小)
                    'pointsInThePaint': stats.get('pointsInPaint', 0)
                }
                new_rows.append(row)
                
        except Exception as e:
            print(f"   ❌ Error parsing game {event.get('id')}: {e}")

    return new_rows

def get_boxscore_stats(game_id, team_id):
    """
    呼叫 Summary API 取得該隊伍的詳細數據 (Debug 版)
    """
    url = f"{ESPN_BASE}/summary?event={game_id}"
    try:
        resp = requests.get(url, timeout=10)
        
        # 1. 檢查 HTTP 狀態碼
        if resp.status_code != 200:
            print(f"   ❌ [Debug] API Request Failed: {resp.status_code} | URL: {url}")
            return None
            
        data = resp.json()
        
        # 2. 檢查是否有 boxscore 欄位
        if 'boxscore' not in data:
            print(f"   ❌ [Debug] JSON 缺少 'boxscore' 欄位。Keys: {list(data.keys())} | Game: {game_id}")
            return None
            
        boxscores = data.get('boxscore', {}).get('teams', [])
        
        # 3. 印出這場比賽有哪些隊伍 ID (確認是否 ID 對不上)
        available_ids = [t['team']['id'] for t in boxscores]
        
        # 找到對應球隊的數據區塊
        # 注意：這裡將 team_id 轉為字串再比較，避免型別不符 (int vs str)
        target = next((t for t in boxscores if str(t['team']['id']) == str(team_id)), None)
        
        if not target:
            # 這是最常見的原因：ID 對不上
            print(f"   ⚠️ [Debug] 找不到 Team ID {team_id}。API 裡的 ID 是: {available_ids}")
            return None
        
        # 4. 檢查是否有 statistics
        stats_list = target.get('statistics', [])
        if not stats_list:
            print(f"   ⚠️ [Debug] Team {team_id} 找到了，但 'statistics' 是空的！")
            return None

        # ESPN 格式是 [{'name': 'fieldGoalsMade', 'value': '40'}, ...]
        stats_map = {}
        for s in stats_list:
            try:
                stats_map[s['name']] = float(s['value'])
            except:
                pass 
        
        return stats_map
        
    except Exception as e:
        print(f"   ❌ [Debug] Exception: {e}")
        return None

def update_csv():
    # 1. 設定目標日期：抓取「昨天」的比賽 (因為今天要訓練昨天的結果)
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    
    new_data = fetch_daily_stats(yesterday)
    
    if not new_data:
        print("📭 沒有新數據需要更新 (可能昨天沒比賽)。")
        return

    df_new = pd.DataFrame(new_data)
    
    # 2. 讀取現有 CSV
    csv_path = 'data/TeamStatistics.csv'
    
    # 確保目錄存在
    os.makedirs('data', exist_ok=True)

    if os.path.exists(csv_path):
        # 讀取舊資料來檢查是否重複
        df_old = pd.read_csv(csv_path, usecols=['gameId', 'teamId'])
        
        # 建立複合鍵檢查 (gameId + teamId)
        existing_keys = set(zip(df_old['gameId'].astype(str), df_old['teamId'].astype(str)))
        
        # 過濾掉已存在的資料
        df_new = df_new[~df_new.apply(lambda x: (str(x['gameId']), str(x['teamId'])) in existing_keys, axis=1)]
        
        if df_new.empty:
            print("✅ 所有數據已存在，無需更新。")
            return
            
        print(f"📦 新增 {len(df_new)} 筆數據到 CSV...")
        
        # Append 模式寫入 (不寫 header)
        # 確保欄位順序正確
        df_new = df_new.reindex(columns=CSV_HEADERS)
        df_new.to_csv(csv_path, mode='a', header=False, index=False)
    else:
        # 如果檔案不存在，建立新檔案 (寫入 header)
        print(f"✨ 建立新的 {csv_path}...")
        df_new = df_new.reindex(columns=CSV_HEADERS)
        df_new.to_csv(csv_path, mode='w', header=True, index=False)
        
    print("🎉 CSV 更新完成！模型現在可以學到最新比賽了。")

if __name__ == "__main__":
    update_csv()