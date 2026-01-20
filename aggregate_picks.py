from config import get_supabase_client

def run_aggregation_engine():
    supabase = get_supabase_client()
    print("1. 正在啟動聚合引擎 (Consensus Engine)...")

    # 1. 取得未來賽事 (只處理 STATUS_SCHEDULED)
    matches_res = supabase.table("matches").select("id, home_team_id, away_team_id").eq("status", "STATUS_SCHEDULED").execute()
    matches = matches_res.data
    
    if not matches:
        print("⚠️ 無待處理賽事。")
        return

    print(f"📊 正在分析 {len(matches)} 場賽事的預測數據...")
    
    aggregated_results = []

    for match in matches:
        match_id = match['id']
        home_team = match['home_team_id']
        away_team = match['away_team_id']

        # 2. 抓取這場比賽的所有預測，並包含來源的權重 (Source Weight)
        # Supabase 的 join 語法：raw_predictions 中關聯 sources
        preds_res = supabase.table("raw_predictions")\
            .select("picked_team_id, sources(weight)")\
            .eq("match_id", match_id)\
            .execute()
        
        predictions = preds_res.data
        
        if not predictions:
            print(f"   Match {match_id}: 無預測數據，跳過。")
            continue

        # 3. 開始計算加權分數
        scores = {home_team: 0.0, away_team: 0.0}
        
        for p in predictions:
            pick = p['picked_team_id']
            # 注意：Supabase 回傳的關聯資料會放在 'sources' 字典裡
            weight = float(p['sources']['weight'])
            
            if pick in scores:
                scores[pick] += weight

        # 4. 判定贏家
        home_score = scores[home_team]
        away_score = scores[away_team]
        total_score = home_score + away_score

        if total_score == 0:
            continue

        if home_score > away_score:
            recommended_team = home_team
            confidence = (home_score / total_score) * 100
        else:
            recommended_team = away_team
            confidence = (away_score / total_score) * 100

        # 準備寫入資料
        result_payload = {
            "match_id": match_id,
            "recommended_team_id": recommended_team,
            "confidence_score": int(confidence),
            "consensus_logic": f"Home({round(home_score,1)}) vs Away({round(away_score,1)})",
            "result_status": "PENDING"
        }
        aggregated_results.append(result_payload)

    # 5. 寫入 aggregated_picks 表
    if aggregated_results:
        print(f"3. 正在生成 {len(aggregated_results)} 筆高信心推薦...")
        # 這裡我們用 upsert，根據 match_id 更新 (需確保 DB 有設 unique，沒設也沒關係，先用 insert 測試)
        # 為了簡單，我們先刪除舊的 (如果有) 再新增，避免重複
        # (正式環境應該用 Upsert，但需要 DB 有設 Unique Key on match_id)
        
        try:
            # 簡單暴力法：先刪除這些比賽的舊推薦，再寫入新的
            match_ids = [r['match_id'] for r in aggregated_results]
            supabase.table("aggregated_picks").delete().in_("match_id", match_ids).execute()
            
            # 寫入新的
            supabase.table("aggregated_picks").insert(aggregated_results).execute()
            print("🎉 聚合完成！推薦結果已儲存。")
            
            # 預覽一筆
            demo = aggregated_results[0]
            print(f"\n--- 推薦範例 (Match {demo['match_id']}) ---")
            print(f"🏆 系統推薦隊伍 ID: {demo['recommended_team_id']}")
            print(f"🔥 信心指數: {demo['confidence_score']}%")
            print(f"📝 權重比分: {demo['consensus_logic']}")
            
        except Exception as e:
            print(f"❌ 寫入失敗: {e}")

if __name__ == "__main__":
    run_aggregation_engine()