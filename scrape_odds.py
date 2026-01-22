import requests
import datetime
import time
from config import get_supabase_client

# 使用 ESPN API 抓取真實盤口
ESPN_SCOREBOARD_URL = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"

def fetch_real_odds():
    supabase = get_supabase_client()
    print("1. 正在初始化真實賠率爬蟲...")

    # 1. 確保 'ESPN BET' 這個來源存在於資料庫
    # 加入重試機制
    source_id = None
    for _ in range(3):
        try:
            source_res = supabase.table("sources").select("id").eq("name", "ESPN BET").execute()
            if not source_res.data:
                print("   建立 'ESPN BET' 來源...")
                s_data = supabase.table("sources").insert({
                    "name": "ESPN BET", 
                    "source_type": "SPORTSBOOK", 
                    "weight": 2.0
                }).execute()
                source_id = s_data.data[0]['id']
            else:
                source_id = source_res.data[0]['id']
            break
        except Exception as e:
            print(f"   ⚠️ 連線來源表失敗，重試中... ({e})")
            time.sleep(2)
            
    if not source_id:
        print("❌ 無法取得 Source ID，停止執行。")
        return

    # 2. 建立球隊查找表
    team_map = {}
    try:
        teams_res = supabase.table("teams").select("id, code").execute()
        team_map = {t['code']: t['id'] for t in teams_res.data}
    except Exception as e:
        print(f"❌ 讀取球隊資料失敗: {e}")
        return

    # 3. 抓取未來賽事的盤口
    today = datetime.datetime.now()
    target_dates = [(today + datetime.timedelta(days=i)).strftime("%Y%m%d") for i in range(-1, 2)]

    odds_data_to_insert = []

    for date_str in target_dates:
        print(f"2. 正在下載 {date_str} 的盤口數據...")
        try:
            response = requests.get(ESPN_SCOREBOARD_URL, params={'dates': date_str}, timeout=10)
            data = response.json()
        except Exception as e:
            print(f"   ⚠️ 下載失敗: {e}")
            continue

        for event in data.get('events', []):
            competition = event['competitions'][0]
            
            try:
                home_team_code = next(filter(lambda x: x['homeAway'] == 'home', competition['competitors']))['team']['abbreviation']
                away_team_code = next(filter(lambda x: x['homeAway'] == 'away', competition['competitors']))['team']['abbreviation']
                
                # 簡單比對 match_id
                match_query = supabase.table("matches").select("id")\
                    .eq("home_team_id", team_map.get(home_team_code))\
                    .eq("away_team_id", team_map.get(away_team_code))\
                    .order("date", desc=True)\
                    .limit(1)
                
                match_res = match_query.execute()
                if not match_res.data:
                    continue 
                
                match_id = match_res.data[0]['id']

                # --- 核心：解析 Odds ---
                if 'odds' in competition and len(competition['odds']) > 0:
                    odds_obj = competition['odds'][0] 
                    
                    # B. 讓分盤 (Spread)
                    spread_str = odds_obj.get('details', '')
                    if spread_str:
                        parts = spread_str.split(' ')
                        if parts[0] != 'EVEN':
                            fav_team_code = parts[0]
                            try:
                                spread_val = float(parts[1]) if len(parts) > 1 else 0
                            except:
                                spread_val = 0
                            
                            picked_team_id = team_map.get(fav_team_code)
                            
                            if picked_team_id:
                                odds_data_to_insert.append({
                                    "match_id": match_id,
                                    "source_id": source_id,
                                    "prediction_type": "SPREAD",
                                    "picked_team_id": picked_team_id,
                                    "line_value": spread_val,
                                    "odds": 1.90,
                                    "selection": None  # <--- 修正點：補上這個 key
                                })

                    # C. 大小分 (Total)
                    total_val = odds_obj.get('overUnder')
                    if total_val:
                        odds_data_to_insert.append({
                            "match_id": match_id,
                            "source_id": source_id,
                            "prediction_type": "TOTAL",
                            "picked_team_id": None,
                            "line_value": total_val,
                            "odds": 1.90,
                            "selection": "Total" # 這裡原本就有，保持一致
                        })

            except Exception as e:
                continue

    # 4. 寫入資料庫
    if odds_data_to_insert:
        print(f"3. 正在寫入 {len(odds_data_to_insert)} 筆真實盤口數據...")
        try:
            supabase.table("raw_predictions").insert(odds_data_to_insert).execute()
            print("🎉 成功！真實盤口已存入。")
        except Exception as e:
            print(f"❌ 寫入失敗: {e}")
    else:
        print("⚠️ 無盤口數據 (可能比賽還沒開盤)")

if __name__ == "__main__":
    fetch_real_odds()