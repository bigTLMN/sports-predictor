from config import get_supabase_client

def grade_picks():
    supabase = get_supabase_client()
    print("1. 正在進行賽果結算 (Grading)...")

    # 1. 抓取所有「還沒結算 (outcome is NULL)」的預測
    # 修改：拿掉 .eq("matches.status", "STATUS_FINAL")，避免 API 報錯
    try:
        picks_res = supabase.table("aggregated_picks")\
            .select("*, matches(*)")\
            .is_("outcome", "null")\
            .execute()
    except Exception as e:
        print(f"❌ 查詢失敗: {e}")
        return
    
    picks = picks_res.data
    
    if not picks:
        print("✅ 目前沒有待結算的預測單。")
        return

    # 統計用
    graded_count = 0

    print(f"2. 掃描 {len(picks)} 筆待結算預測，尋找已完賽場次...")
    
    for pick in picks:
        match = pick['matches']
        
        # --- 修正點：在這裡用 Python 檢查比賽狀態 ---
        # 如果比賽還沒打完 (不是 STATUS_FINAL)，就跳過
        if not match or match.get('status') != 'STATUS_FINAL':
            continue
            
        match_id = pick['match_id']
        
        # 取得比分
        home_score = match['home_score']
        away_score = match['away_score']
        
        # 確保比分存在 (避免 API 資料有缺)
        if home_score is None or away_score is None:
            continue

        result = None
        line_val = 0.0

        # --- A. 結算讓分盤 (Spread) ---
        if pick.get('recommended_team_id') and pick.get('line_info'):
            rec_team_id = pick['recommended_team_id']
            
            # 解析盤口字串 (e.g., "Line: -5.5" -> -5.5)
            try:
                line_str = pick['line_info'].replace("Line: ", "").replace("Spread: ", "")
                line_val = float(line_str)
            except:
                print(f"⚠️ 無法解析盤口數值: {pick['line_info']}，跳過此單")
                continue
            
            # 計算分差
            score_diff = home_score - away_score 
            is_home_pick = (rec_team_id == match['home_team_id'])
            
            # 轉換為「推薦隊伍的淨勝分」
            real_diff = score_diff if is_home_pick else -score_diff
            
            # 判斷輸贏
            if (real_diff + line_val) > 0:
                result = "WIN"
            elif (real_diff + line_val) < 0:
                result = "LOSS"
            else:
                result = "PUSH"

            # 寫入結果
            try:
                supabase.table("aggregated_picks").update({"outcome": result}).eq("id", pick['id']).execute()
                print(f"   📝 MATCH {match_id}: Picked Team {rec_team_id} ({line_val}) -> {result}")
                graded_count += 1
            except Exception as e:
                print(f"   ❌ 寫入結果失敗: {e}")

        # --- B. 結算大小分 (O/U) - 如果你有做的話 ---
        if pick.get('ou_pick') and pick.get('ou_line'):
             # (這裡保留擴充空間)
             pass

    if graded_count > 0:
        print(f"🎉 成功結算 {graded_count} 筆預測！")
    else:
        print("✅ 掃描完畢，沒有發現新的已完賽場次。")

if __name__ == "__main__":
    grade_picks()