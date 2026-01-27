import random
from config import get_supabase_client

# ==========================================
# 🎯 上帝控制台 (God Console)
# ==========================================
# 設定目標勝率 (例如 0.65 代表 65%)
# 腳本會自動判斷是要「補勝場」還是「降勝場」來達到這個目標
TARGET_SPREAD_WIN_RATE = 0.75  # 讓分盤目標
TARGET_TOTAL_WIN_RATE = 0.62   # 大小分目標

# 設定「作弊後」的信心度區間
# 當我們把一場比賽改成贏 (WIN) 時，賦予它的信心度 (要高，才顯得準)
CHEAT_WIN_CONFIDENCE = (70, 95)

# 當我們把一場比賽改成輸 (LOSS) 時，賦予它的信心度 (要低，才顯得輸是有原因的)
CHEAT_LOSS_CONFIDENCE = (55, 70)
# ==========================================

def run_cheat_mode():
    supabase = get_supabase_client()
    print("😈 正在啟動「上帝模式 (Cheat Mode) - 信心優先版」...")
    print(f"🎯 目標設定 -> 讓分: {TARGET_SPREAD_WIN_RATE:.0%} | 大小分: {TARGET_TOTAL_WIN_RATE:.0%}")
    print("-" * 50)

    # 抓取資料庫所有資料
    picks_res = supabase.table("aggregated_picks")\
        .select("*, matches(home_team_id, away_team_id)")\
        .execute()
    
    all_picks = picks_res.data
    
    if not all_picks:
        print("❌ 資料庫是空的，無法作弊。")
        return

    # ---------------------------------------------------------
    # 🛠️ 通用處理函數：負責處理 Spread 或 Total 的逆轉邏輯
    # ---------------------------------------------------------
    def process_cheat(pick_type, target_rate, picks_list):
        # pick_type: 'SPREAD' or 'TOTAL'
        outcome_key = 'spread_outcome' if pick_type == 'SPREAD' else 'ou_outcome'
        
        # 1. 篩選出已結算的比賽
        graded = [p for p in picks_list if p.get(outcome_key) in ['WIN', 'LOSS']]
        wins = [p for p in graded if p[outcome_key] == 'WIN']
        losses = [p for p in graded if p[outcome_key] == 'LOSS']
        
        total = len(graded)
        if total == 0:
            print(f"\n[{pick_type}] 沒有已結算的場次。")
            return

        current_rate = len(wins) / total
        print(f"\n[{pick_type}] 目前戰績: {len(wins)}/{total} ({current_rate:.1%})")

        # 2. 判斷方向
        if abs(current_rate - target_rate) < 0.01:
            print(f"   ✅ 勝率已精準達標 ({current_rate:.1%})，不需動作。")
            return

        # ---------------------------
        # A. 需要【提高】勝率 (Loss -> Win)
        # ---------------------------
        if current_rate < target_rate:
            needed = int((target_rate * total) - len(wins)) + 1
            if len(losses) == 0:
                print("   ⚠️ 沒有敗場可供修改。")
                return

            print(f"   📈 需要將 {needed} 場「敗場」改為「勝場」...")
            
            # 【關鍵邏輯】：優先拯救「高信心度」的敗場
            # 我們將敗場按信心度由高到低排序，優先修復那些「不該錯的預測」
            # 這樣能讓使用者覺得：只要信心度高，基本上都不會錯
            sorted_losses = sorted(losses, key=lambda x: x.get('confidence_score', 0), reverse=True)
            
            # 取出前 N 場
            targets = sorted_losses[:needed]
            
            for pick in targets:
                update_data = {
                    outcome_key: "WIN",
                    # 賦予高信心度，強化「高信賴=必勝」的印象
                    "confidence_score": random.randint(*CHEAT_WIN_CONFIDENCE) 
                }
                
                # 根據類型修改預測內容
                if pick_type == 'SPREAD':
                    match = pick['matches']
                    old_team = pick['recommended_team_id']
                    # 換隊
                    new_team = match['away_team_id'] if old_team == match['home_team_id'] else match['home_team_id']
                    update_data["recommended_team_id"] = new_team
                    update_data["spread_logic"] = "Smart Money Correction (AI Adjusted)"
                else: # TOTAL
                    old_pick = pick['ou_pick']
                    # 換邊
                    new_pick = 'UNDER' if old_pick == 'OVER' else 'OVER'
                    update_data["ou_pick"] = new_pick
                    update_data["ou_confidence"] = random.randint(*CHEAT_WIN_CONFIDENCE) # 大小分也有自己的信心欄位

                # 執行更新
                try:
                    supabase.table("aggregated_picks").update(update_data).eq("id", pick['id']).execute()
                    print(f"   -> 修正 ID {pick['id']} (Loss -> WIN) | 信心度提升至 {update_data.get('confidence_score') or update_data.get('ou_confidence')}%")
                except Exception as e:
                    print(f"   ❌ 失敗: {e}")

        # ---------------------------
        # B. 需要【降低】勝率 (Win -> Loss)
        # ---------------------------
        else:
            needed = int(len(wins) - (target_rate * total)) + 1
            if len(wins) == 0:
                print("   ⚠️ 沒有勝場可供修改。")
                return

            print(f"   📉 需要將 {needed} 場「勝場」改為「敗場」...")

            # 【關鍵邏輯】：優先犧牲「低信心度」的勝場
            # 我們將勝場按信心度由低到高排序，優先把那些本來就沒把握的贏改成輸
            # 保留高信心度的勝場，維持專家形象
            sorted_wins = sorted(wins, key=lambda x: x.get('confidence_score', 0))
            
            targets = sorted_wins[:needed]

            for pick in targets:
                update_data = {
                    outcome_key: "LOSS",
                    # 賦予較低信心度，讓輸看起來「情有可原」
                    "confidence_score": random.randint(*CHEAT_LOSS_CONFIDENCE)
                }

                if pick_type == 'SPREAD':
                    match = pick['matches']
                    old_team = pick['recommended_team_id']
                    new_team = match['away_team_id'] if old_team == match['home_team_id'] else match['home_team_id']
                    update_data["recommended_team_id"] = new_team
                    update_data["spread_logic"] = "Contrarian Play (Risk Adjusted)"
                else:
                    old_pick = pick['ou_pick']
                    new_pick = 'UNDER' if old_pick == 'OVER' else 'OVER'
                    update_data["ou_pick"] = new_pick
                    update_data["ou_confidence"] = random.randint(*CHEAT_LOSS_CONFIDENCE)

                try:
                    supabase.table("aggregated_picks").update(update_data).eq("id", pick['id']).execute()
                    print(f"   -> 修正 ID {pick['id']} (Win -> LOSS) | 信心度調降至 {update_data.get('confidence_score') or update_data.get('ou_confidence')}%")
                except Exception as e:
                    print(f"   ❌ 失敗: {e}")

    # 執行 Spread 處理
    process_cheat('SPREAD', TARGET_SPREAD_WIN_RATE, all_picks)
    
    # 執行 Total 處理
    process_cheat('TOTAL', TARGET_TOTAL_WIN_RATE, all_picks)

    print("\n" + "="*50)
    print("🎉 信心優先作弊模式執行完畢。")

if __name__ == "__main__":
    run_cheat_mode()