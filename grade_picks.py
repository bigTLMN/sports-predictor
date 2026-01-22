from config import get_supabase_client

def grade_picks():
    supabase = get_supabase_client()
    print("1. 正在進行賽果結算 (Dual Grading)...")

    # 1. 抓取所有「還沒完全結算」的預測 (任一欄位是 NULL 且比賽已打完)
    # 這裡我們放寬標準：只要比賽是 FINAL，我們就重新檢查一次所有欄位
    try:
        picks_res = supabase.table("aggregated_picks")\
            .select("*, matches(*)")\
            .execute()
    except Exception as e:
        print(f"❌ 查詢失敗: {e}")
        return
    
    picks = picks_res.data
    updates_count = 0

    print(f"2. 掃描 {len(picks)} 筆預測，進行雙重對獎...")
    
    for pick in picks:
        match = pick['matches']
        
        # 只有已完賽的才算分
        if not match or match.get('status') != 'STATUS_FINAL':
            continue
            
        # 取得比分
        home_score = match['home_score']
        away_score = match['away_score']
        
        if home_score is None or away_score is None:
            continue

        updates = {}
        should_update = False

        # --- A. 結算讓分盤 (Spread) ---
        # 只有當 spread_outcome 還沒填，且有推薦隊伍時才算
        if pick.get('recommended_team_id') and pick.get('line_info') and not pick.get('spread_outcome'):
            try:
                rec_team_id = pick['recommended_team_id']
                line_str = pick['line_info'].replace("Line: ", "").replace("Spread: ", "").replace("PK", "0")
                line_val = float(line_str)
                
                # 計算：(主隊-客隊)
                score_diff = home_score - away_score 
                is_home_pick = (rec_team_id == match['home_team_id'])
                real_diff = score_diff if is_home_pick else -score_diff
                
                if (real_diff + line_val) > 0:
                    updates["spread_outcome"] = "WIN"
                elif (real_diff + line_val) < 0:
                    updates["spread_outcome"] = "LOSS"
                else:
                    updates["spread_outcome"] = "PUSH"
                
                should_update = True
                print(f"   [Spread] Match {match['id']}: {updates['spread_outcome']}")
            except Exception as e:
                print(f"   ⚠️ Spread 計算錯誤: {e}")

        # --- B. 結算大小分 (Total) ---
        # 只有當 ou_outcome 還沒填，且有預測大小分時才算
        if pick.get('ou_pick') and pick.get('ou_line') and not pick.get('ou_outcome'):
            try:
                pick_type = pick['ou_pick'] # 'OVER' or 'UNDER'
                line_val = float(pick['ou_line'])
                total_score = home_score + away_score
                
                result = "PUSH"
                if total_score > line_val:
                    result = "WIN" if pick_type == 'OVER' else "LOSS"
                elif total_score < line_val:
                    result = "WIN" if pick_type == 'UNDER' else "LOSS"
                
                updates["ou_outcome"] = result
                should_update = True
                print(f"   [Total] Match {match['id']}: {total_score} vs {line_val} ({pick_type}) -> {result}")
            except Exception as e:
                print(f"   ⚠️ Total 計算錯誤: {e}")

        # --- 執行更新 ---
        if should_update:
            supabase.table("aggregated_picks").update(updates).eq("id", pick['id']).execute()
            updates_count += 1

    print(f"🎉 結算完成！共更新 {updates_count} 筆資料。")

if __name__ == "__main__":
    grade_picks()