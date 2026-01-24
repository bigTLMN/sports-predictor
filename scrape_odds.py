import requests
import datetime
import time
import re
from config import get_supabase_client

# 使用 ESPN API 抓取真實盤口
ESPN_SCOREBOARD_URL = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"

def get_team_map(supabase):
    """建立球隊代碼對照表 (Code -> ID)"""
    # 注意：ESPN 的代碼通常跟我們的一樣 (LAL, BOS, GSW...)
    # 唯獨要注意 UTAH (ESPN用UTA), NO (ESPN用NOP), NY (ESPN用NYK), SA (ESPN用SAS), GS (ESPN用GSW)
    # 這裡做一個簡單的轉換字典
    mapping_fix = {
        'UTA': 'UTAH', 'NOP': 'NO', 'NYK': 'NY', 'SAS': 'SA', 'GSW': 'GS', 'WSH': 'WSH'
    }
    
    teams = supabase.table("teams").select("id, code").execute().data
    team_map = {}
    for t in teams:
        team_map[t['code']] = t['id']
        # 加上反向對應，確保 ESPN 的標準代碼也能找到
        for espn_code, my_code in mapping_fix.items():
            if my_code == t['code']:
                team_map[espn_code] = t['id']
                
    return team_map

def fetch_real_odds():
    supabase = get_supabase_client()
    print("📊 啟動真實盤口更新 (Source: ESPN)...")

    # 1. 準備工具
    team_map = get_team_map(supabase)
    
    # 2. 抓取範圍：今天、明天
    today = datetime.datetime.now()
    target_dates = [(today + datetime.timedelta(days=i)).strftime("%Y%m%d") for i in range(2)]

    total_updated = 0

    for date_str in target_dates:
        print(f"   -> 正在檢查 {date_str} 的盤口...")
        try:
            response = requests.get(ESPN_SCOREBOARD_URL, params={'dates': date_str}, timeout=10)
            data = response.json()
        except Exception as e:
            print(f"      ⚠️ 下載失敗: {e}")
            continue

        events = data.get('events', [])
        if not events:
            print("      📭 該日無比賽資料")
            continue

        for event in events:
            try:
                competition = event['competitions'][0]
                competitors = competition['competitors']
                
                # 取得主客隊代碼
                home_comp = next(filter(lambda x: x['homeAway'] == 'home', competitors))
                away_comp = next(filter(lambda x: x['homeAway'] == 'away', competitors))
                
                home_abbr = home_comp['team']['abbreviation']
                away_abbr = away_comp['team']['abbreviation']
                
                h_id = team_map.get(home_abbr)
                a_id = team_map.get(away_abbr)
                
                if not h_id or not a_id:
                    # print(f"      ⚠️ 找不到球隊 ID: {home_abbr} vs {away_abbr}")
                    continue

                # --- 核心：解析 Odds ---
                vegas_spread = None
                vegas_total = None

                if 'odds' in competition and len(competition['odds']) > 0:
                    odds_obj = competition['odds'][0] # 通常取第一個莊家 (ESPN BET)
                    
                    # 1. 解析讓分 (Spread)
                    # 格式通常是 "BOS -5.5" 或 "LAL -3.0"
                    details = odds_obj.get('details', '')
                    if details:
                        try:
                            # 分割字串，例如 "BOS -5.5" -> ["BOS", "-5.5"]
                            parts = details.split(' ')
                            if len(parts) >= 2:
                                favored_team = parts[0]
                                spread_val = float(parts[1])
                                
                                # 轉換邏輯：我們資料庫存的是「主隊讓分」
                                # 如果 Favored 是主隊，Spread = -5.5
                                # 如果 Favored 是客隊，Spread = +5.5 (代表主隊受讓)
                                
                                # 處理 ESPN 有時代碼不一致的問題 (e.g. NYK vs NY)
                                # 我們比對是否 favored_team 在主隊的 mapping key 裡
                                is_home_favored = (favored_team == home_abbr)
                                
                                if is_home_favored:
                                    vegas_spread = spread_val if spread_val < 0 else -spread_val
                                else:
                                    vegas_spread = abs(spread_val) # 客隊讓分，主隊就是正的
                        except:
                            pass

                    # 2. 解析大小分 (Over/Under)
                    # 格式通常在 overUnder 欄位，例如 225.5
                    ou_val = odds_obj.get('overUnder')
                    if ou_val:
                        vegas_total = float(ou_val)

                # --- 寫入資料庫 ---
                # 只有當我們抓到了盤口才更新
                if vegas_spread is not None or vegas_total is not None:
                    # 尋找對應的比賽 (未開打)
                    # 我們用 team ID 來找，不限制日期 (自動對應最近的一場)
                    
                    # 先查詢 ID
                    matches = supabase.table("matches").select("id")\
                        .eq("home_team_id", h_id)\
                        .eq("away_team_id", a_id)\
                        .eq("status", "STATUS_SCHEDULED")\
                        .execute().data
                    
                    if matches:
                        match_id = matches[0]['id']
                        
                        update_data = {}
                        if vegas_spread is not None: update_data["vegas_spread"] = vegas_spread
                        if vegas_total is not None: update_data["vegas_total"] = vegas_total
                        
                        supabase.table("matches").update(update_data).eq("id", match_id).execute()
                        # print(f"      ✅ 更新盤口: {away_abbr} @ {home_abbr} -> Spread: {vegas_spread}, Total: {vegas_total}")
                        total_updated += 1

            except Exception as e:
                # print(f"      ❌ 解析錯誤: {e}")
                pass

    print(f"🎉 完成！已更新 {total_updated} 場比賽的真實盤口。")

if __name__ == "__main__":
    fetch_real_odds()