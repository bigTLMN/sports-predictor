import random
from config import get_supabase_client

def generate_mock_predictions():
    supabase = get_supabase_client()
    
    print("1. 取得尚未開打的比賽 (Real Matches)...")
    # 這裡我們只抓狀態是 SCHEDULED 的比賽
    matches_res = supabase.table("matches").select("id, home_team_id, away_team_id").eq("status", "STATUS_SCHEDULED").execute()
    matches = matches_res.data
    
    if not matches:
        print("⚠️ 目前沒有 'SCHEDULED' 的比賽，無法生成預測。請確認 scrape_schedule.py 是否有抓到未來的比賽。")
        return

    print(f"📊 找到 {len(matches)} 場待賽，準備生成預測數據...")

    print("2. 取得預測來源 (Sources)...")
    sources_res = supabase.table("sources").select("id, name").execute()
    sources = sources_res.data # e.g., [{'id': 1, 'name': 'ESPN'}, {'id': 2, 'name': 'Vegas'}]

    predictions_to_insert = []

    for match in matches:
        match_id = match['id']
        home_team = match['home_team_id']
        away_team = match['away_team_id']
        
        # 針對每一個來源，都產生一個預測
        for source in sources:
            # 隨機決定這個來源看好誰 (模擬真實世界的預測)
            # 這裡我們用 50/50 機率，你可以改成讓 Vegas 更準一點
            predicted_winner = random.choice([home_team, away_team])
            
            # 隨機產生賠率 (模擬 1.5 ~ 2.5 之間的賠率)
            random_odds = round(random.uniform(1.5, 2.5), 2)
            
            # 建立預測資料 Payload
            pred = {
                "match_id": match_id,
                "source_id": source['id'],
                "picked_team_id": predicted_winner,
                "prediction_type": "MONEYLINE", # 獨贏
                "odds": random_odds
            }
            predictions_to_insert.append(pred)

    print(f"3. 正在寫入 {len(predictions_to_insert)} 筆模擬預測...")
    
    try:
        # 這裡不使用 upsert，因為預測可能會變動，我們先用 insert 簡單測試
        # 實務上我們會檢查是否已存在，但 MVP 先求有
        supabase.table("raw_predictions").insert(predictions_to_insert).execute()
        print("🎉 成功！模擬預測數據已注入資料庫！")
        
        # 預覽結果
        print("\n--- 預測資料預覽 ---")
        for p in predictions_to_insert[:3]:
            # 為了顯示方便，這裡簡略印出 ID
            s_name = next(s['name'] for s in sources if s['id'] == p['source_id'])
            print(f"💡 [{s_name}] 預測 Match {p['match_id']} -> 贏家 ID: {p['picked_team_id']} (賠率: {p['odds']})")
            
    except Exception as e:
        print(f"❌ 寫入失敗：{e}")

if __name__ == "__main__":
    generate_mock_predictions()