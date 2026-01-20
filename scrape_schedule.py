import requests
import datetime
from config import get_supabase_client

# ESPN 賽程 API
ESPN_SCOREBOARD_URL = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"

def fetch_and_store_schedule():
    supabase = get_supabase_client()
    
    print("1. 正在建立球隊查找表...")
    teams_response = supabase.table("teams").select("id, code").execute()
    team_map = {team['code']: team['id'] for team in teams_response.data}
    
    league_res = supabase.table("leagues").select("id").eq("name", "NBA").execute()
    nba_league_id = league_res.data[0]['id']

    # --- 修改重點開始：我們要抓未來 3 天的比賽 ---
    today = datetime.datetime.now()
    # 產生今天、明天、後天的日期列表 (格式 YYYYMMDD)
    target_dates = [(today + datetime.timedelta(days=i)).strftime("%Y%m%d") for i in range(3)]
    
    print(f"2. 準備抓取這些日期的賽程: {target_dates}")

    total_matches_processed = 0

    for date_str in target_dates:
        print(f"   正在下載 {date_str} 的賽程...", end="")
        
        # 加上 dates 參數，強制指定日期
        response = requests.get(ESPN_SCOREBOARD_URL, params={'dates': date_str})
        data = response.json()
        events = data.get('events', [])
        print(f" 找到 {len(events)} 場")

        matches_to_insert = []
        
        for event in events:
            competition = event['competitions'][0]
            match_date = competition['date']
            
            # 處理主客隊
            try:
                home_data = next(filter(lambda x: x['homeAway'] == 'home', competition['competitors']))
                away_data = next(filter(lambda x: x['homeAway'] == 'away', competition['competitors']))
            except StopIteration:
                continue # 資料不完整跳過

            home_code = home_data['team']['abbreviation']
            away_code = away_data['team']['abbreviation']
            
            home_id = team_map.get(home_code)
            away_id = team_map.get(away_code)
            
            if not home_id or not away_id:
                continue

            status_type = event['status']['type']['name']
            
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
                
            matches_to_insert.append(match_payload)

        # 寫入資料庫
        if matches_to_insert:
            try:
                supabase.table("matches").upsert(matches_to_insert).execute()
                total_matches_processed += len(matches_to_insert)
            except Exception as e:
                print(f"\n❌ 寫入失敗 ({date_str}): {e}")

    print(f"\n🎉 完成！共處理了 {total_matches_processed} 場比賽。")

if __name__ == "__main__":
    fetch_and_store_schedule()