import pandas as pd
import numpy as np
import joblib
import os
import json
import re # 🔥 新增：正則表達式，用來清理字串
from datetime import datetime, timedelta
from supabase import create_client
from config import get_supabase_client
# 🔥 引入傷兵爬蟲模組
from utils.fetch_injuries import fetch_injury_report 

# ==========================================
# 設定：只預測未來 1 天 (配合 CI/CD 每日執行)
# ==========================================
PREDICT_DAYS = 1 
CHEAT_MODE = os.getenv("CHEAT_MODE", "false").lower() == "true"

print(f"📂 [V9.5] 正在載入 AI 模型與戰力庫... (Cheat Mode: {CHEAT_MODE})")
try:
    # 載入模型 (根目錄)
    model_win = joblib.load('model_win.pkl')
    model_spread = joblib.load('model_spread.pkl')
    model_total = joblib.load('model_total.pkl')
    features_spread = joblib.load('features_spread.pkl')
    features_total = joblib.load('features_total.pkl')
    
    # 載入窗口設定
    try:
        ROLLING_WINDOWS = joblib.load('rolling_config.pkl')
        print(f"   ⚙️ 載入動態窗口設定: {ROLLING_WINDOWS}")
    except:
        ROLLING_WINDOWS = [5, 10, 30]
        print(f"   ⚠️ 未找到 rolling_config.pkl，使用預設窗口: {ROLLING_WINDOWS}")

    # 🔥 載入球員戰力庫 (修正為根目錄讀取)
    player_impact_map = joblib.load('player_impact_map.pkl')
    team_rosters = joblib.load('team_rosters.pkl')
    print(f"   ✅ 戰力庫載入成功 (球員數: {len(player_impact_map)})")

except Exception as e:
    print(f"❌ 模型載入失敗: {e}")
    print("   請確認你有執行過 train_model.py 和 utils/export_impact_data.py")
    exit()

# 基礎欄位
BASE_STATS_COLS = [
    'fieldGoalsPercentage', 'threePointersPercentage', 'freeThrowsPercentage',
    'reboundsTotal', 'assists', 'steals', 'blocks', 'turnovers', 
    'plusMinusPoints', 'pointsInThePaint', 'teamScore', 
    'eFG_Percentage', 'TS_Percentage', 'RestDays',
    'roster_impact_score' 
]

def normalize_name(name):
    """🔥 新增：標準化球員姓名 (取代危險的模糊比對)"""
    if not isinstance(name, str):
        return ""
    name = name.lower()
    # 去除標點符號 (如 O'Neale -> oneale)
    name = re.sub(r"[^\w\s]", "", name)
    # 去除常見後綴 (jr, sr, ii, iii)
    name = re.sub(r"\s+(jr|sr|ii|iii|iv)$", "", name)
    return name.strip()

def calculate_live_impact(team_id, injury_report):
    """計算即時戰力分數：拿完整陣容扣除傷兵 (改用精準正規化比對)"""
    if team_id not in team_rosters:
        return 100.0, [], 0.0
    
    full_roster = team_rosters[team_id] 
    current_impact = 0.0
    missing_impact = 0.0
    missing_players = []
    
    # 🔥 預先清理 ESPN 抓下來的傷兵名單 key
    normalized_injury_report = {normalize_name(k): v for k, v in injury_report.items()}
    
    for player in full_roster:
        impact = player_impact_map.get(player, 0)
        
        # 標準化我們資料庫中的球員名字
        norm_player = normalize_name(player)
        
        # 🔥 改用「正規化後的精準比對」，徹底消滅 Jovic/Jokic 誤判事件
        if norm_player in normalized_injury_report:
            miss_prob = normalized_injury_report[norm_player] # 取得 1.0, 0.75, 0.5 或 0.0
            
            impact_lost = impact * miss_prob
            missing_impact += impact_lost
            current_impact += (impact - impact_lost)
            
            # 只有主力且真的有扣到戰力 (miss_prob > 0) 才顯示在文字戰報中
            if impact > 10 and miss_prob > 0:
                status_label = "OUT" if miss_prob >= 0.75 else "GTD"
                missing_players.append(f"{player}({status_label})")
        else:
            current_impact += impact
            
    return current_impact, missing_players, missing_impact

# 🧠 AI 洞察生成核心
def generate_insight(rec_code, opp_code, is_home_pick, features_df, h_missing, a_missing, h_code, a_code):
    analysis_text = []

    # 1. 🔥 傷兵影響分析
    if h_missing:
        analysis_text.append(f"⚠️ {h_code} missing: {', '.join(h_missing)}.")
    if a_missing:
        analysis_text.append(f"⚠️ {a_code} missing: {', '.join(a_missing)}.")

    # 2. 戰力落差分析
    if 'diff_roster_impact' in features_df.columns:
        impact_diff = features_df['diff_roster_impact'].iloc[0]
        if abs(impact_diff) > 15:
            stronger = h_code if impact_diff > 0 else a_code
            analysis_text.append(f"Significant roster advantage for {stronger} (+{abs(impact_diff):.1f} impact).")

    # 3. 數據優勢分析 (近 5 場)
    feature_map = {
        'diff_rolling_5_threePointersPercentage': '3PT Shooting',
        'diff_rolling_5_reboundsTotal': 'Rebounding',
        'diff_rolling_5_steals': 'Defense',
        'diff_rolling_5_turnovers': 'Ball Control', 
        'diff_rolling_5_win_rate': 'Recent Form'
    }

    if not features_df.empty:
        row = features_df.iloc[0]
        factors = []
        for col, name in feature_map.items():
            if col not in row: continue
            val = row[col]
            
            is_good = False
            if 'turnovers' in col:
                if is_home_pick and val < -2: is_good = True 
                elif not is_home_pick and val > 2: is_good = True 
            else:
                if is_home_pick and val > 0: is_good = True
                elif not is_home_pick and val < 0: is_good = True
            
            if is_good:
                factors.append(name)

        if factors:
            analysis_text.append(f"{rec_code} has the edge in {', '.join(factors[:2])}.")

    if not analysis_text:
        return f"AI projects a close matchup favoring {rec_code} based on recent trends."
    
    return " ".join(analysis_text)

def get_latest_stats():
    print("🔄 [V9.5] 讀取並計算多重窗口統計 (含平均 Impact)...")
    try:
        req_cols = [
            'teamId', 'gameDateTimeEst', 'win', 'teamScore', 
            'fieldGoalsMade', 'fieldGoalsAttempted', 'threePointersMade', 
            'freeThrowsAttempted',
            'fieldGoalsPercentage', 'threePointersPercentage', 'freeThrowsPercentage',
            'reboundsTotal', 'assists', 'steals', 'blocks', 'turnovers', 
            'plusMinusPoints', 'pointsInThePaint'
        ]
        df = pd.read_csv('data/TeamStatistics.csv', usecols=lambda c: c in req_cols, low_memory=False)
        
        df['gameDateTimeEst'] = pd.to_datetime(df['gameDateTimeEst'], utc=True, errors='coerce')
        df = df.dropna(subset=['gameDateTimeEst']).sort_values(['teamId', 'gameDateTimeEst'])
        
        df['threePointersMade'] = df['threePointersMade'].fillna(0)
        df['fieldGoalsAttempted'] = df['fieldGoalsAttempted'].replace(0, np.nan)
        df['eFG_Percentage'] = (df['fieldGoalsMade'] + 0.5 * df['threePointersMade']) / df['fieldGoalsAttempted']
        df['TS_Percentage'] = df['teamScore'] / (2 * (df['fieldGoalsAttempted'] + 0.44 * df['freeThrowsAttempted']))
        df['eFG_Percentage'] = df['eFG_Percentage'].fillna(0)
        df['TS_Percentage'] = df['TS_Percentage'].fillna(0)

        df['prev_game_date'] = df.groupby('teamId')['gameDateTimeEst'].shift(1)
        df['RestDays'] = (df['gameDateTimeEst'] - df['prev_game_date']).dt.days
        df['RestDays'] = df['RestDays'].fillna(3).clip(upper=7)
        
        if df['win'].isnull().any(): df = df.dropna(subset=['win'])
        df['win_numeric'] = df['win'].astype(int)
        
        df['roster_impact_score'] = 100.0

        cols_to_roll = [c for c in BASE_STATS_COLS if c in df.columns and c != 'RestDays']
        cols_to_roll.append('RestDays')

        rolled_dfs = []
        for w in ROLLING_WINDOWS:
            r_stats = df.groupby('teamId', group_keys=False)[cols_to_roll].apply(
                lambda x: x.rolling(w, min_periods=1).mean()
            )
            r_stats.columns = [f'rolling_{w}_{c}' for c in r_stats.columns]
            
            r_win = df.groupby('teamId', group_keys=False)['win_numeric'].apply(
                lambda x: x.rolling(w, min_periods=1).mean()
            )
            r_stats[f'rolling_{w}_win_rate'] = r_win
            
            rolled_dfs.append(r_stats)
            
        df = pd.concat([df] + rolled_dfs, axis=1)
        
        last = df.groupby('teamId').tail(1)
        keep_cols = [c for c in df.columns if 'rolling_' in c]
        
        result = {}
        for _, r in last.iterrows():
            result[int(r['teamId'])] = {c: r[c] for c in keep_cols}
            
        return result
        
    except Exception as e:
        print(f"❌ 讀取 TeamStatistics 失敗: {e}")
        return {}

def prepare_features(h_id, a_id, stats, h_impact, a_impact, h_avg_impact, a_avg_impact):
    if h_id not in stats or a_id not in stats: return None, None, None
    h, a = stats[h_id], stats[a_id]
    
    row = {'is_home': 1}
    
    for key in h.keys():
        if key in a:
            row[f"diff_{key}"] = h[key] - a[key]
            row[f"sum_{key}"] = h[key] + a[key]
            
    row['roster_impact_score'] = h_impact 
    row['diff_roster_impact'] = h_impact - a_impact
    
    row['missing_impact_h'] = h_impact - h_avg_impact
    row['missing_impact_a'] = a_impact - a_avg_impact
    row['diff_missing_impact'] = row['missing_impact_h'] - row['missing_impact_a']

    df = pd.DataFrame([row])
    
    for c in features_spread: 
        if c not in df.columns: df[c] = 0
    for c in features_total: 
        if c not in df.columns: df[c] = 0
    
    return df[features_spread], df[features_total], df

def run():
    supabase = get_supabase_client()
    stats = get_latest_stats()
    if not stats: return

    injury_report = fetch_injury_report() 

    now = datetime.utcnow()
    end_date = now + timedelta(days=PREDICT_DAYS)
    
    print(f"📅 抓取賽程範圍: {now.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")

    matches = supabase.table("matches")\
        .select("*, home_team:teams!matches_home_team_id_fkey(code, nba_team_id), away_team:teams!matches_away_team_id_fkey(code, nba_team_id)")\
        .gte("date", now.isoformat())\
        .lt("date", end_date.isoformat())\
        .order('date')\
        .execute().data

    if not matches:
        print("📭 無比賽。")
        return

    print(f"🤖 準備掃描 {len(matches)} 場比賽...")
    picks = []
    
    for m in matches:
        try:
            status = m.get('status', '')
            locked_statuses = ['STATUS_IN_PROGRESS', 'STATUS_FINAL', 'STATUS_FINISHED', 'STATUS_POSTPONED', 'In Progress', 'Final']
            
            if status in locked_statuses and not CHEAT_MODE:
                print(f"   ⏩ 防呆跳過: {m['away_team']['code']} @ {m['home_team']['code']} (狀態: {status}，已開打或結束)")
                continue            
            h_id = int(m['home_team']['nba_team_id'])
            a_id = int(m['away_team']['nba_team_id'])
            
            h_impact, h_missing_names, _ = calculate_live_impact(h_id, injury_report)
            a_impact, a_missing_names, _ = calculate_live_impact(a_id, injury_report)
            
            h_avg_impact = stats[h_id].get('rolling_10_roster_impact_score', 100)
            a_avg_impact = stats[a_id].get('rolling_10_roster_impact_score', 100)

            X_spr, X_tot, raw_df = prepare_features(
                h_id, a_id, stats, 
                h_impact, a_impact, 
                h_avg_impact, a_avg_impact
            )
            if X_spr is None: continue

            win_prob = float(model_win.predict_proba(X_spr)[0][1])
            pred_margin = float(model_spread.predict(X_spr)[0]) 
            pred_total = float(model_total.predict(X_tot)[0])

            vegas_spread = m.get('vegas_spread', 0.0) or 0.0
            vegas_total = m.get('vegas_total', 225.0) or 225.0
            
            predicted_cover_margin = pred_margin + vegas_spread
            
            if predicted_cover_margin > 1.5: 
                rec_id = m['home_team_id']
                rec_code = m['home_team']['code']
                opp_code = m['away_team']['code']
                is_rec_home = True
            elif predicted_cover_margin < -1.5: 
                rec_id = m['away_team_id']
                rec_code = m['away_team']['code']
                opp_code = m['home_team']['code']
                is_rec_home = False
            else:
                if win_prob > 0.55:
                    rec_id = m['home_team_id']
                    rec_code = m['home_team']['code']
                    opp_code = m['away_team']['code']
                    is_rec_home = True
                else:
                    rec_id = m['away_team_id']
                    rec_code = m['away_team']['code']
                    opp_code = m['home_team']['code']
                    is_rec_home = False

            edge = abs(predicted_cover_margin)
            conf = min(50 + int(edge * 5), 95)
            
            ou_pick = "OVER" if pred_total > vegas_total else "UNDER"
            ou_conf = min(50 + int(abs(pred_total - vegas_total) * 3), 90)

            analysis_text = generate_insight(
                rec_code, opp_code, is_rec_home, raw_df,
                h_missing_names, a_missing_names,
                m['home_team']['code'], m['away_team']['code']
            )

            picks.append({
                "match_id": m['id'],
                "predicted_winner_id": m['home_team_id'] if win_prob > 0.5 else m['away_team_id'],
                "win_probability": win_prob, 
                "predicted_margin": pred_margin,
                "predicted_total": pred_total,
                "recommended_team_id": rec_id,
                "confidence_score": conf,
                "spread_logic": analysis_text, 
                "ou_pick": ou_pick,
                "ou_confidence": ou_conf,
                "line_info": str(vegas_spread),
                "created_at": datetime.utcnow().isoformat()
            })
            print(f"   -> {m['away_team']['code']} @ {m['home_team']['code']}: [{rec_code}] {analysis_text[:50]}...")

        except Exception as e:
            print(f"⚠️ Error {m['id']}: {e}")

    if picks:
        try:
            match_ids = [p['match_id'] for p in picks]
            existing = supabase.table("aggregated_picks").select("*").in_("match_id", match_ids).execute().data
            existing_map = {item['match_id']: item for item in existing}
            
            for p in picks:
                if p['match_id'] in existing_map:
                    old_data = existing_map[p['match_id']]
                    p['id'] = old_data['id']
                    
                    history = old_data.get('history', [])
                    if not history:
                        history = []
                        
                    is_changed = (
                        old_data.get('line_info') != p['line_info'] or 
                        old_data.get('recommended_team_id') != p['recommended_team_id']
                    )
                    
                    if is_changed:
                        old_timestamp = old_data.get('created_at', 'Unknown Time')
                        old_rec_id = old_data.get('recommended_team_id')
                        
                        history_entry = {
                            "time": old_timestamp,
                            "logic": old_data.get('spread_logic', ''),
                            "line": old_data.get('line_info', ''),
                            "team_id": old_rec_id
                        }
                        history.append(history_entry)
                    
                    p['history'] = history
            
            supabase.table("aggregated_picks").upsert(picks).execute()
            print(f"✅ 完成！已更新 {len(picks)} 筆預測 (包含歷史軌跡)。")
        except Exception as e:
            print(f"❌ 寫入 Supabase 失敗: {e}")
    else:
        print("✅ 無需更新。")

if __name__ == "__main__":
    run()