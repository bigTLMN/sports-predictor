import random
from config import get_supabase_client

def run_aggregation_engine():
    supabase = get_supabase_client()
    print("1. 正在啟動進階聚合引擎 (Spread + O/U)...")

    # 1. 抓取未來賽事
    matches_res = supabase.table("matches").select("id, home_team_id, away_team_id").eq("status", "STATUS_SCHEDULED").execute()
    matches = matches_res.data
    
    if not matches:
        print("⚠️ 無待處理賽事。")
        return

    aggregated_results = []

    for match in matches:
        match_id = match['id']
        
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

        # --- A. 讓分盤邏輯 (Spread Strategy) ---
        if spread_data:
            vegas_line = float(spread_data['line_value']) # 莊家盤口，例如 -5.5 (主隊讓5.5)
            fav_team_id = spread_data['picked_team_id']
            
            # [模擬專家模型]：我們模擬一個「真實實力預測」
            # 邏輯：莊家盤口 +/- 3分的誤差範圍內波動
            # 如果 expert_diff > vegas_line，代表專家比莊家更看好讓分方 -> 買讓分
            # 如果 expert_diff < vegas_line，代表專家覺得讓太多了 -> 買受讓
            
            variance = random.uniform(-4.0, 4.0) 
            expert_projected_diff = vegas_line + variance 
            
            # 判斷推薦誰
            if expert_projected_diff < vegas_line: 
                # 專家預測分差(-8) 比 盤口(-5.5) 更大 (注意負數) -> 讓分方會大勝
                # 買讓分方
                rec_team = fav_team_id
                logic_msg = f"Model projects win by {abs(round(expert_projected_diff,1))}, covers {spread_data['line_value']}"
            else:
                # 專家預測分差(-3) 比 盤口(-5.5) 小 -> 讓分方贏不夠多，甚至輸
                # 買受讓方 (對家)
                if fav_team_id == match['home_team_id']:
                    rec_team = match['away_team_id']
                else:
                    rec_team = match['home_team_id']
                logic_msg = f"Value Play: Taking points vs {spread_data['line_value']}"

            result["recommended_team_id"] = rec_team
            result["confidence_score"] = random.randint(60, 95) # 模擬信心度
            result["line_info"] = f"Line: {spread_data['line_value']}"
            result["spread_logic"] = logic_msg
            result["consensus_logic"] = "Smart Money Model" # 前端顯示用

        # --- B. 大小分邏輯 (Over/Under Strategy) ---
        if total_data:
            vegas_total = float(total_data['line_value']) # e.g. 220.5
            
            # [模擬專家模型] 產生一個預測總分
            projected_total = vegas_total + random.uniform(-10, 10)
            
            if projected_total > vegas_total:
                result["ou_pick"] = "OVER"
                result["ou_confidence"] = random.randint(60, 90)
            else:
                result["ou_pick"] = "UNDER"
                result["ou_confidence"] = random.randint(60, 90)
                
            result["ou_line"] = vegas_total

        # 只有當至少有一種預測時才存入
        if "recommended_team_id" in result:
            aggregated_results.append(result)

    # 3. 寫入資料庫
    if aggregated_results:
        print(f"3. 生成 {len(aggregated_results)} 筆進階預測 (含讓分/受讓/大小)...")
        match_ids = [r['match_id'] for r in aggregated_results]
        try:
            supabase.table("aggregated_picks").delete().in_("match_id", match_ids).execute()
            supabase.table("aggregated_picks").insert(aggregated_results).execute()
            print("🎉 預測更新完成！")
        except Exception as e:
            print(f"❌ 寫入失敗: {e}")

if __name__ == "__main__":
    run_aggregation_engine()