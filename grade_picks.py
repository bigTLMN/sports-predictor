from config import get_supabase_client
import pandas as pd

def grade_picks():
    supabase = get_supabase_client()
    print("1. 正在進行賽果結算 (Grading)...")

    # 1. 抓取所有已完賽的比賽
    try:
        matches = supabase.table("matches")\
            .select("*, home_team:teams!matches_home_team_id_fkey(code), away_team:teams!matches_away_team_id_fkey(code)")\
            .in_("status", ["STATUS_FINAL", "STATUS_FINISHED", "Final"])\
            .execute().data
            
        if not matches:
            print("📭 無已完賽的比賽。")
            return
        
        # 建立 match_id -> match 對照表
        finished_matches = {m['id']: m for m in matches}
        
    except Exception as e:
        print(f"❌ 查詢比賽失敗: {e}")
        return

    # 2. 抓取所有尚未結算的預測
    try:
        # 🔥 修正 1：改為「只要 spread 或 total 有一個沒結算，就抓出來」
        picks = supabase.table("aggregated_picks").select("*").or_("spread_outcome.is.null,total_outcome.is.null").execute().data
    except Exception as e:
        print(f"❌ 查詢預測失敗: {e}")
        return

    if not picks:
        print("✅ 無需結算的預測。")
        return

    updates_count = 0
    print(f"2. 掃描 {len(picks)} 筆待結算預測...")
    
    for pick in picks:
        match_id = pick['match_id']
        if match_id not in finished_matches:
            continue
            
        match = finished_matches[match_id]
        
        # 取得比分
        home_score = match['home_score']
        away_score = match['away_score']
        
        if home_score is None or away_score is None:
            continue

        updates = {}
        should_update = False

        # --- A. 結算讓分盤 (Spread) ---
        # 如果還沒結算才算
        if pick.get('spread_outcome') is None and pick.get('line_info'):
            try:
                line_val = float(pick['line_info'])
                rec_team_id = pick['recommended_team_id']
                
                # 計算主隊贏分
                home_margin = home_score - away_score
                
                if rec_team_id == match['home_team_id']:
                    if (home_margin + line_val) > 0: result = "WIN"
                    elif (home_margin + line_val) < 0: result = "LOSS"
                    else: result = "PUSH"
                else:
                    if (home_margin + line_val) > 0: result = "LOSS" 
                    elif (home_margin + line_val) < 0: result = "WIN"
                    else: result = "PUSH"

                updates["spread_outcome"] = result
                should_update = True
            except Exception as e:
                print(f"   ⚠️ Spread Error ID {pick['id']}: {e}")

        # --- B. 結算大小分 (Total) ---
        # 🔥 修正 2：直接去找 match['vegas_total'] 當作盤口依據
        if pick.get('total_outcome') is None and pick.get('ou_pick') and match.get('vegas_total'):
            try:
                pick_type = pick['ou_pick']
                line_val = float(match['vegas_total'])
                total_score = home_score + away_score
                
                result = "PUSH"
                if total_score > line_val:
                    result = "WIN" if pick_type == 'OVER' else "LOSS"
                elif total_score < line_val:
                    result = "WIN" if pick_type == 'UNDER' else "LOSS"
                
                updates["total_outcome"] = result 
                should_update = True
            except Exception as e:
                print(f"   ⚠️ Total Error ID {pick['id']}: {e}")

        # --- 執行更新 ---
        if should_update:
            try:
                supabase.table("aggregated_picks").update(updates).eq("id", pick['id']).execute()
                updates_count += 1
                
                h_code = match['home_team']['code'] if match.get('home_team') else 'HOME'
                a_code = match['away_team']['code'] if match.get('away_team') else 'AWAY'
                
                print(f"   ✅ Match {a_code} @ {h_code} -> {updates}")
            except Exception as e:
                print(f"   ❌ Update Failed ID {pick['id']}: {e}")

    print(f"🎉 結算完成！共更新 {updates_count} 筆資料。")

if __name__ == "__main__":
    grade_picks()