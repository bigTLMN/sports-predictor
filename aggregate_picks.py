import random
from config import get_supabase_client

def run_aggregation_engine():
    supabase = get_supabase_client()
    print("1. 正在啟動進階聚合引擎 (鎖定模式)...")

    # 1. 抓取未來賽事 (STATUS_SCHEDULED)
    matches_res = supabase.table("matches")\
        .select("id, home_team_id, away_team_id")\
        .eq("status", "STATUS_SCHEDULED")\
        .execute()
    matches = matches_res.data
    
    if not matches:
        print("⚠️ 無待處理賽事。")
        return

    # --- 新增邏輯：先找出「已經預測過」的比賽 ID ---
    # 我們不希望覆蓋舊的預測，所以要先建立一個「已鎖定清單」
    existing_picks_res = supabase.table("aggregated_picks").select("match_id").execute()
    existing_match_ids = set(item['match_id'] for item in existing_picks_res.data)

    new_picks = []
    skipped_count = 0

    for match in matches:
        match_id = match['id']
        
        # [關鍵鎖定]：如果這場比賽已經有預測了，直接跳過！
        # 這保證了昨天的預測今天看不會變，且今天的重跑不會覆蓋昨天的結果
        if match_id in existing_match_ids:
            skipped_count += 1
            continue

        # 2. 抓取這場比賽的真實盤口 (ESPN BET)
        odds_res = supabase.table("raw_predictions")\
            .select("*")\
            .eq("match_id", match_id)\
            .order("crawled_at", desc=True)\
            .execute()
        
        odds_list = odds_res.data
        if not odds_list: continue

        spread_data = next((x for x in odds_list if x['prediction_type'] == 'SPREAD'), None)
        total_data = next((x for x in odds_list if x['prediction_type'] == 'TOTAL'), None)

        # 初始化結果容器
        result = {
            "match_id": match_id,
            "result_status": "PENDING"
        }

        # --- A. 讓分盤邏輯 ---
        if spread_data:
            vegas_line = float(spread_data['line_value'])
            fav_team_id = spread_data['picked_team_id']
            
            # 模擬專家模型 (這裡的 variance 生成後就會被寫入資料庫並永久固定)
            variance = random.uniform(-4.0, 4.0) 
            expert_projected_diff = vegas_line + variance 
            
            if expert_projected_diff < vegas_line: 
                rec_team = fav_team_id
                logic_msg = f"Model projects win by {abs(round(expert_projected_diff,1))}, covers {spread_data['line_value']}"
            else:
                if fav_team_id == match['home_team_id']:
                    rec_team = match['away_team_id']
                else:
                    rec_team = match['home_team_id']
                logic_msg = f"Value Play: Taking points vs {spread_data['line_value']}"

            result["recommended_team_id"] = rec_team
            result["confidence_score"] = random.randint(60, 95)
            result["line_info"] = f"Line: {spread_data['line_value']}"
            result["spread_logic"] = logic_msg
            result["consensus_logic"] = "Smart Money Model"

        # --- B. 大小分邏輯 ---
        if total_data:
            vegas_total = float(total_data['line_value'])
            projected_total = vegas_total + random.uniform(-10, 10)
            
            if projected_total > vegas_total:
                result["ou_pick"] = "OVER"
                result["ou_confidence"] = random.randint(60, 90)
            else:
                result["ou_pick"] = "UNDER"
                result["ou_confidence"] = random.randint(60, 90)
            result["ou_line"] = vegas_total

        # 只有當產生了有效預測才加入清單
        if "recommended_team_id" in result:
            new_picks.append(result)

    # 3. 寫入資料庫 (只 Insert 新的，不 Delete 舊的)
    if new_picks:
        print(f"3. 生成 {len(new_picks)} 筆新預測 (跳過 {skipped_count} 筆已鎖定預測)...")
        try:
            # 這裡只用 insert，不再先 delete 了
            supabase.table("aggregated_picks").insert(new_picks).execute()
            print("🎉 新增預測完成！")
        except Exception as e:
            print(f"❌ 寫入失敗: {e}")
    else:
        print(f"✅ 沒有新的預測產生 (跳過 {skipped_count} 筆已存在的預測)。")

if __name__ == "__main__":
    run_aggregation_engine()