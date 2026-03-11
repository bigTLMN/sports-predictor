import requests
import time
from datetime import datetime, timedelta
from config import get_supabase_client

# 改用 ESPN API (穩定、不擋 IP、含各節比分與盤口)
ESPN_API_URL = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"

def get_team_map(supabase):
    """建立球隊代碼對照表 (Code -> ID)"""
    mapping_fix = {
        'UTA': 'UTAH', 'NOP': 'NO', 'NYK': 'NY', 'SAS': 'SA', 'GSW': 'GS', 'WSH': 'WSH'
    }
    
    teams = supabase.table('teams').select('id, code').execute().data
    team_map = {}
    for t in teams:
        team_map[t['code']] = t['id']
        for espn_code, my_code in mapping_fix.items():
            if my_code == t['code']:
                team_map[espn_code] = t['id']
    return team_map

def scrape_schedule():
    supabase = get_supabase_client()
    team_map = get_team_map(supabase)
    
    # 抓取範圍：過去 3 天到未來 3 天
    today = datetime.now()
    dates_to_scrape = [(today + timedelta(days=i)).strftime('%Y%m%d') for i in range(-3, 4)]
    
    print(f"🕵️‍♂️ 啟動賽程與盤口更新 (來源: ESPN)，目標日期: {dates_to_scrape}")
    
    total_processed = 0

    for date_str in dates_to_scrape:
        display_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        print(f"   -> 正在檢查 {display_date} ...")
        
        try:
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
                        continue
                        
                    h_id = team_map[home_abbr]
                    a_id = team_map[away_abbr]

                    # 狀態判斷
                    espn_status = event['status']['type']['name']
                    if espn_status == 'STATUS_FINAL':
                        status = "STATUS_FINISHED"
                    elif espn_status in ['STATUS_IN_PROGRESS', 'STATUS_HALFTIME', 'STATUS_END_PERIOD']:
                        status = "STATUS_IN_PROGRESS"
                    elif espn_status in ['STATUS_POSTPONED', 'STATUS_CANCELED']:
                        status = "STATUS_POSTPONED"
                    else:
                        status = "STATUS_SCHEDULED"

                    # 處理總分
                    h_score = int(home_comp['score']) if home_comp.get('score') else 0
                    a_score = int(away_comp['score']) if away_comp.get('score') else 0
                    
                    # 處理各節比分
                    period_scores_json = None
                    if 'linescores' in home_comp and 'linescores' in away_comp:
                        h_lines = [int(x['value']) for x in home_comp['linescores'] if 'value' in x]
                        a_lines = [int(x['value']) for x in away_comp['linescores'] if 'value' in x]
                        if h_lines or a_lines:
                            period_scores_json = {"home": h_lines, "away": a_lines}

                    # 🔥 新增：抓取盤口資訊 (Vegas Odds)
                    vegas_spread = None
                    vegas_total = None
                    odds_info = competition.get('odds')
                    if odds_info and len(odds_info) > 0:
                        odd_data = odds_info[0]
                        vegas_total = odd_data.get('overUnder')
                        details = odd_data.get('details', '')
                        
                        if details.upper() in ['EVEN', 'PICK', 'PK']:
                            vegas_spread = 0.0
                        elif details:
                            parts = details.split(' ')
                            if len(parts) >= 2:
                                try:
                                    fav_team = parts[0]
                                    spread_val = float(parts[1])
                                    # 如果 ESPN 讓分方是主隊，vegas_spread 記錄為該負值
                                    # 如果讓分方是客隊，主隊的 spread 則為正值
                                    if fav_team == home_abbr:
                                        vegas_spread = spread_val
                                    else:
                                        vegas_spread = -spread_val
                                except Exception as e:
                                    pass

                    # 準備寫入資料
                    match_data = {
                        "date": display_date,
                        "start_time": event['date'],
                        "home_team_id": h_id,
                        "away_team_id": a_id,
                        "status": status,
                        "home_score": h_score,
                        "away_score": a_score,
                        "period_scores": period_scores_json
                    }

                    # 只有抓到盤口時才更新，避免把舊盤口洗掉
                    if vegas_spread is not None:
                        match_data["vegas_spread"] = vegas_spread
                    if vegas_total is not None:
                        match_data["vegas_total"] = vegas_total

                    # Upsert 邏輯
                    existing = supabase.table('matches').select('id')\
                        .eq('date', display_date)\
                        .eq('home_team_id', h_id)\
                        .eq('away_team_id', a_id)\
                        .execute().data
                    
                    if existing:
                        match_id = existing[0]['id']
                        supabase.table('matches').update(match_data).eq('id', match_id).execute()
                    else:
                        supabase.table('matches').insert(match_data).execute()
                        print(f"      ➕ 新增: {away_abbr} @ {home_abbr}")
                    
                    total_processed += 1

                except Exception as e:
                    print(f"      ❌ 處理錯誤 ({away_abbr} vs {home_abbr}): {e}")

            time.sleep(0.5)

        except Exception as e:
            print(f"      ❌ 連線錯誤: {e}")

    print(f"🎉 完成！共處理 {total_processed} 場比賽 (ESPN Source)。")

if __name__ == "__main__":
    scrape_schedule()