import requests
from config import get_supabase_client

# 這是 ESPN 的公開 API，回傳非常乾淨的 JSON 格式
ESPN_NBA_TEAMS_URL = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams"

def fetch_and_store_teams():
    supabase = get_supabase_client()

    print("1. 正在取得 NBA 聯盟 ID...")
    # 先從 DB 找出 NBA 的 ID (避免寫死 ID=1，萬一變了會報錯)
    league_response = supabase.table("leagues").select("id").eq("name", "NBA").execute()
    
    if not league_response.data:
        print("❌ 錯誤：找不到 NBA 聯盟資料，請先執行 main.py 建立聯盟。")
        return
        
    nba_league_id = league_response.data[0]['id']
    print(f"✅ 取得 NBA ID: {nba_league_id}")

    print("2. 正在從 ESPN API 下載球隊資料...")
    # 發送請求給 ESPN
    response = requests.get(ESPN_NBA_TEAMS_URL)
    data = response.json()
    
    # 解析 JSON 資料
    teams_to_insert = []
    # ESPN 的 JSON 結構比較深，不用擔心，這是標準結構
    raw_teams = data.get('sports', [])[0].get('leagues', [])[0].get('teams', [])
    
    print(f"📊 找到 {len(raw_teams)} 支球隊，正在整理數據...")

    for item in raw_teams:
        team_info = item['team']
        
        # 整理成我們資料庫要的格式
        team_payload = {
            "league_id": nba_league_id,
            "name": team_info.get('shortDisplayName'),  # e.g., Lakers
            "full_name": team_info.get('displayName'),  # e.g., Los Angeles Lakers
            "code": team_info.get('abbreviation'),      # e.g., LAL
            "logo_url": team_info.get('logos', [{}])[0].get('href') # 抓第一張 Logo
        }
        teams_to_insert.append(team_payload)

    print("3. 正在寫入 Supabase 資料庫...")
    try:
        # 批量寫入 (Batch Insert)
        result = supabase.table("teams").upsert(teams_to_insert).execute()
        print("🎉 成功！已將 30 支球隊資料存入資料庫！")
        
        # 顯示前 3 筆驗證
        print("\n--- 預覽前 3 筆資料 ---")
        for team in result.data[:3]:
            print(f"🏀 {team['code']} - {team['full_name']}")
            
    except Exception as e:
        print(f"❌ 寫入失敗：{e}")

if __name__ == "__main__":
    fetch_and_store_teams()