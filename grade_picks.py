from config import get_supabase_client

def grade_picks():
    supabase = get_supabase_client()
    print("1. 正在進行賽果結算 (Grading)...")

    # 1. 抓取所有「還沒結算 (outcome is NULL)」的預測
    # 並且這場比賽必須已經打完 (status = STATUS_FINAL)
    picks_res = supabase.table("aggregated_picks")\
        .select("*, matches(*)")\
        .is_("outcome", "null")\
        .eq("matches.status", "STATUS_FINAL")\
        .execute()
    
    picks = picks_res.data
    if not picks:
        print("✅ 目前沒有需要結算的預測。")
        return

    print(f"2. 發現 {len(picks)} 筆待結算預測，開始對答案...")
    
    updates = []

    for pick in picks:
        match = pick['matches']
        match_id = pick['match_id']
        
        # 取得比分
        home_score = match['home_score']
        away_score = match['away_score']
        
        # --- A. 結算讓分盤 (Spread) ---
        if pick.get('recommended_team_id'):
            rec_team_id = pick['recommended_team_id']
            line = float(pick['line_info'].replace("Line: ", "")) # 解析 "-5.5" 字串
            
            # 計算分差 (主隊 - 客隊)
            score_diff = home_score - away_score 
            
            # 判斷讓分結果
            # 邏輯：如果你買主隊，你的分數是 (Score Diff)，如果要贏盤口，Score Diff 必須 > 盤口
            # 舉例：LAL -5.5。LAL贏10分 (Diff=10)。 10 > 5.5 -> WIN
            # 舉例：LAL -5.5。LAL贏 2分 (Diff= 2)。 2 > 5.5 -> FALSE (LOSS)
            
            is_home_pick = (rec_team_id == match['home_team_id'])
            
            # 調整：為了方便計算，我們統一轉成「推薦隊伍的淨勝分」
            real_diff = score_diff if is_home_pick else -score_diff
            
            # 這裡的 line 通常是負數 (e.g. -5.5) 代表讓分，正數 (+5.5) 代表受讓
            # 勝利條件：(真實淨勝分 + 讓分值) > 0
            # 舉例：買讓分 -5.5，贏 6 分 -> 6 + (-5.5) = 0.5 > 0 -> WIN
            # 舉例：買受讓 +5.5，輸 4 分 -> -4 + 5.5 = 1.5 > 0 -> WIN
            
            if (real_diff + line) > 0:
                result = "WIN"
            elif (real_diff + line) < 0:
                result = "LOSS"
            else:
                result = "PUSH" # 剛好平手 (運彩少見，但在整數盤口會有)

            # 寫入結果
            supabase.table("aggregated_picks").update({"outcome": result}).eq("id", pick['id']).execute()
            print(f"   MATCH {match_id}: Picked Team ID {rec_team_id} ({line}) -> Result: {result}")

        # --- B. 結算大小分 (O/U) ---
        # (這裡留給你練習擴充，邏輯類似：Home+Away > Line 就是 OVER)

    print("🎉 結算完成！")

if __name__ == "__main__":
    grade_picks()