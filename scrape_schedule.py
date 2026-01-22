import requests
import datetime
import time
from config import get_supabase_client

# ESPN 賽程 API
ESPN_SCOREBOARD_URL = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"

def fetch_and_store_schedule():
    supabase = get_supabase_client()
    
    print("1. 正在建立球隊查找表 (含喚醒重試機制)...")
    
    team_map = {}
    nba_league_id = None
    
    # --- 重試機制 ---
    for attempt in range(1, 4):
        try:
            print(f"   連線嘗試第 {attempt} 次...")
            teams_response = supabase.table("teams").select("id, code").execute()
            team_map = {team['code']: team['id'] for team in teams_response.data}
            
            league_res = supabase.table("leagues").select("id").eq("name", "NBA").execute()
            nba_league_id = league_res.data[0]['id']
            
            print("   ✅ 資料庫連線成功！")
            break 
        except Exception as e:
            print(f"   ⚠️ 連線失敗 (可能是資料庫正在喚醒中): {e}")
            if attempt < 3:
                print("   ⏳ 等待 10 秒後重試...")
                time.sleep(10)
            else:
                print("❌ 錯誤：無法連線到資料庫，請檢查 Supabase 是否正常運作。")
                return
    
    # 抓取未來賽程
    today = datetime.datetime.now()
    target_dates = [(today + datetime.timedelta(days=i)).strftime("%Y%m%d") for i in range(-1, 2)]
    
    print(f"2. 準備抓取這些日期的賽程: {target_dates}")

    total_matches_processed = 0

    for date_str in target_dates:
        print(f"   正在下載 {date_str} 的賽程...", end="")
        
        try:
            response = requests.get(ESPN_SCOREBOARD_URL, params={'dates': date_str}, timeout=10)
            data = response.json()
            events = data.get('events', [])
            print(f" 找到 {len(events)} 場")

            for event in events:
                competition = event['competitions'][0]
                match_date = competition['date']
                
                try:
                    home_data = next(filter(lambda x: x['homeAway'] == 'home', competition['competitors']))
                    away_data = next(filter(lambda x: x['homeAway'] == 'away', competition['competitors']))
                except StopIteration:
                    continue 

                home_code = home_data['team']['abbreviation']
                away_code = away_data['team']['abbreviation']
                
                home_id = team_map.get(home_code)
                away_id = team_map.get(away_code)
                
                if not home_id or not away_id:
                    continue

                status_type = event['status']['type']['name']
                
                # 準備要寫入的資料
                match_payload = {
                    "league_id": nba_league_id,
                    "season": competition.get('season', {}).get('year'),
                    "date": match_date,
                    "start_time": match_date,
                    "home_team_id": home_id,
                    "away_team_id": away_id,
                    "status": status_type,
                    "home_score": int(home_data.get('score', 0)),
                    "away_score": int(away_data.get('score', 0))
                }
                
                if status_type == 'STATUS_FINAL':
                    match_payload['winner_team_id'] = home_id if match_payload['home_score'] > match_payload['away_score'] else away_id
                
                # --- 修改重點：手動檢查並更新 (Manual Upsert) ---
                try:
                    # 1. 檢查這場比賽是否已存在 (用 日期 + 主隊 + 客隊 判斷)
                    existing = supabase.table("matches")\
                        .select("id")\
                        .eq("date", match_date)\
                        .eq("home_team_id", home_id)\
                        .eq("away_team_id", away_id)\
                        .execute()
                    
                    if existing.data:
                        # 2. 如果存在 -> 更新 (Update)
                        existing_id = existing.data[0]['id']
                        supabase.table("matches").update(match_payload).eq("id", existing_id).execute()
                        # print(f"      🔄 更新比賽: {home_code} vs {away_code}")
                    else:
                        # 3. 如果不存在 -> 新增 (Insert)
                        supabase.table("matches").insert(match_payload).execute()
                        print(f"      ➕ 新增比賽: {home_code} vs {away_code}")
                        
                    total_matches_processed += 1
                    
                except Exception as e:
                    print(f"      ❌ 處理單場失敗: {e}")

        except Exception as e:
            print(f"\n❌ 下載失敗 ({date_str}): {e}")

    print(f"\n🎉 完成！共處理了 {total_matches_processed} 場比賽。")

if __name__ == "__main__":
    fetch_and_store_schedule()