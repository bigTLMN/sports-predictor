import requests
import time
from datetime import datetime, timedelta
from config import get_supabase_client

# 改用 ESPN API (穩定、不擋 IP)
ESPN_API_URL = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"

def get_team_map(supabase):
    """建立球隊代碼對照表 (Code -> ID)，包含 ESPN 特殊代碼轉換"""
    # ESPN 的代碼有時候跟我們的稍微不一樣，這裡做對應
    mapping_fix = {
        'UTA': 'UTAH', 'NOP': 'NO', 'NYK': 'NY', 'SAS': 'SA', 'GSW': 'GS', 'WSH': 'WSH'
    }
    
    teams = supabase.table('teams').select('id, code').execute().data
    team_map = {}
    for t in teams:
        team_map[t['code']] = t['id']
        # 加上反向對應
        for espn_code, my_code in mapping_fix.items():
            if my_code == t['code']:
                team_map[espn_code] = t['id']
    return team_map

def scrape_schedule():
    supabase = get_supabase_client()
    team_map = get_team_map(supabase)
    
    # 設定抓取範圍：昨天、今天、明天、後天
    today = datetime.now()
    dates_to_scrape = [(today + timedelta(days=i)).strftime('%Y%m%d') for i in range(-1, 3)]
    
    print(f"🕵️‍♂️ 啟動賽程更新 (來源: ESPN)，目標日期: {dates_to_scrape}")
    
    total_processed = 0

    for date_str in dates_to_scrape:
        # 格式化顯示用日期 (YYYY-MM-DD)
        display_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        print(f"   -> 正在檢查 {display_date} ...")
        
        try:
            # ESPN API 只需要 dates 參數，不需要複雜 Header
            resp = requests.get(ESPN_API_URL, params={'dates': date_str}, timeout=10)
            if resp.status_code != 200:
                print(f"      ⚠️ API 錯誤: {resp.status_code}")
                continue

            data = resp.json()
            events = data.get('events', [])
            
            if not events:
                print("      📭 無比賽")
                continue
            
            for event in events:
                try:
                    competition = event['competitions'][0]
                    competitors = competition['competitors']
                    
                    # 抓取主客隊資料
                    home_comp = next(filter(lambda x: x['homeAway'] == 'home', competitors))
                    away_comp = next(filter(lambda x: x['homeAway'] == 'away', competitors))
                    
                    home_abbr = home_comp['team']['abbreviation']
                    away_abbr = away_comp['team']['abbreviation']
                    
                    if home_abbr not in team_map or away_abbr not in team_map:
                        # print(f"      ⚠️ 找不到球隊: {away_abbr} @ {home_abbr}")
                        continue
                        
                    h_id = team_map[home_abbr]
                    a_id = team_map[away_abbr]

                    # 狀態判斷
                    # ESPN status type: 'STATUS_SCHEDULED', 'STATUS_FINAL', 'STATUS_IN_PROGRESS'
                    espn_status = event['status']['type']['name']
                    if espn_status == 'STATUS_FINAL':
                        status = "STATUS_FINISHED"
                    elif espn_status == 'STATUS_IN_PROGRESS':
                        status = "STATUS_IN_PROGRESS"
                    else:
                        status = "STATUS_SCHEDULED"

                    # 處理分數
                    h_score = int(home_comp['score']) if home_comp.get('score') else 0
                    a_score = int(away_comp['score']) if away_comp.get('score') else 0
                    
                    # 準備寫入資料
                    match_data = {
                        "date": display_date,  # 強制對齊查詢日期 (YYYY-MM-DD)
                        "start_time": event['date'], # ESPN 給的是 ISO UTC 時間
                        "home_team_id": h_id,
                        "away_team_id": a_id,
                        "status": status,
                        "home_score": h_score,
                        "away_score": a_score
                    }

                    # ==========================================
                    # 🔥 穩健寫入邏輯：先檢查，後動作
                    # ==========================================
                    existing = supabase.table('matches').select('id')\
                        .eq('date', display_date)\
                        .eq('home_team_id', h_id)\
                        .eq('away_team_id', a_id)\
                        .execute().data
                    
                    if existing:
                        # 存在 -> Update
                        match_id = existing[0]['id']
                        supabase.table('matches').update(match_data).eq('id', match_id).execute()
                    else:
                        # 不存在 -> Insert
                        supabase.table('matches').insert(match_data).execute()
                        print(f"      ➕ 新增: {away_abbr} @ {home_abbr}")
                    
                    total_processed += 1

                except Exception as e:
                    print(f"      ❌ 處理錯誤: {e}")

            time.sleep(0.5) # ESPN 很耐操，稍微休息即可

        except Exception as e:
            print(f"      ❌ 連線錯誤: {e}")

    print(f"🎉 完成！共處理 {total_processed} 場比賽 (ESPN Source)。")

if __name__ == "__main__":
    scrape_schedule()