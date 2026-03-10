import pandas as pd
import numpy as np
import os

# 🏀 NBA 隊名 (Nickname) 轉 ID 對照表
# 這是為了讓 PlayerStatistics (只有隊名) 能對齊 TeamStatistics (只有 ID)
TEAM_NAME_TO_ID = {
    'Hawks': 1610612737, 'Celtics': 1610612738, 'Cavaliers': 1610612739, 'Pelicans': 1610612740,
    'Bulls': 1610612741, 'Mavericks': 1610612742, 'Nuggets': 1610612743, 'Warriors': 1610612744,
    'Rockets': 1610612745, 'Clippers': 1610612746, 'Lakers': 1610612747, 'Heat': 1610612748,
    'Bucks': 1610612749, 'Timberwolves': 1610612750, 'Nets': 1610612751, 'Knicks': 1610612752,
    'Magic': 1610612753, 'Pacers': 1610612754, '76ers': 1610612755, 'Suns': 1610612756,
    'Trail Blazers': 1610612757, 'Kings': 1610612758, 'Spurs': 1610612759, 'Thunder': 1610612760,
    'Raptors': 1610612761, 'Jazz': 1610612762, 'Grizzlies': 1610612763, 'Wizards': 1610612764,
    'Pistons': 1610612765, 'Hornets': 1610612766
}

def calculate_game_score(row):
    try:
        # 轉換數值，若有空值填 0
        pts = float(row['points']) if pd.notna(row['points']) else 0
        fg = float(row['fieldGoalsMade']) if pd.notna(row['fieldGoalsMade']) else 0
        fga = float(row['fieldGoalsAttempted']) if pd.notna(row['fieldGoalsAttempted']) else 0
        ft = float(row['freeThrowsMade']) if pd.notna(row['freeThrowsMade']) else 0
        fta = float(row['freeThrowsAttempted']) if pd.notna(row['freeThrowsAttempted']) else 0
        orb = float(row['reboundsOffensive']) if pd.notna(row['reboundsOffensive']) else 0
        drb = float(row['reboundsDefensive']) if pd.notna(row['reboundsDefensive']) else 0
        stl = float(row['steals']) if pd.notna(row['steals']) else 0
        ast = float(row['assists']) if pd.notna(row['assists']) else 0
        blk = float(row['blocks']) if pd.notna(row['blocks']) else 0
        pf = float(row['foulsPersonal']) if pd.notna(row['foulsPersonal']) else 0
        tov = float(row['turnovers']) if pd.notna(row['turnovers']) else 0

        # GameScore 公式
        gm_score = pts + 0.4 * fg - 0.7 * fga - 0.4 * (fta - ft) + 0.7 * orb + 0.3 * drb + stl + 0.7 * ast + 0.7 * blk - 0.4 * pf - tov
        return gm_score
    except Exception:
        return 0

def get_season(date_obj):
    if date_obj.month >= 10:
        return date_obj.year + 1
    return date_obj.year

def process_player_impact():
    print("🔄 [Step 1] 讀取 PlayerStatistics.csv ...")
    
    # 根據你提供的欄位，這裡有 playerteamName (例如 'Bucks')
    cols = ['gameId', 'personId', 'gameDateTimeEst', 'points', 
            'fieldGoalsMade', 'fieldGoalsAttempted', 
            'freeThrowsMade', 'freeThrowsAttempted', 
            'reboundsOffensive', 'reboundsDefensive', 
            'steals', 'assists', 'blocks', 'foulsPersonal', 'turnovers', 
            'playerteamName'] 

    df_players = pd.read_csv('data/PlayerStatistics.csv', usecols=lambda c: c in cols, low_memory=False)

    # 基礎清理
    df_players = df_players.fillna(0)
    df_players['gameId'] = df_players['gameId'].astype(str) # 統一轉字串
    
    # 🔥 關鍵修正：將 playerteamName (Bucks) 轉成 teamId (1610612749)
    print("🔄 [Step 2] 轉換隊名為 Team ID (Align with TeamStatistics)...")
    df_players['teamId'] = df_players['playerteamName'].map(TEAM_NAME_TO_ID)
    
    # 檢查有沒有對應不到的隊伍 (例如資料庫有舊隊名)
    missing_teams = df_players[df_players['teamId'].isna()]['playerteamName'].unique()
    if len(missing_teams) > 0:
        print(f"⚠️ 警告: 以下隊名無法轉換為 ID (可能是明星賽或舊隊名): {missing_teams}")
        df_players = df_players.dropna(subset=['teamId']) # 移除無法辨識的列
    
    # 轉為 int (跟 TeamStatistics 一致)
    df_players['teamId'] = df_players['teamId'].astype(int)

    # 處理日期與賽季
    print("🔄 [Step 3] 處理賽季資訊...")
    df_players['gameDateTimeEst'] = pd.to_datetime(df_players['gameDateTimeEst'])
    df_players['season'] = df_players['gameDateTimeEst'].apply(get_season)

    # 計算 GameScore
    print("🔄 [Step 4] 計算單場 GameScore...")
    df_players['game_score'] = df_players.apply(calculate_game_score, axis=1)

    print("🔄 [Step 5] 計算球員賽季平均戰力 (Season Average Impact)...")
    # 這裡計算的是：該球員在「當季」的平均貢獻值
    season_avg = df_players.groupby(['season', 'personId'])['game_score'].transform('mean')
    df_players['player_season_impact'] = season_avg

    print("🔄 [Step 6] 聚合每場比賽的陣容強度 (Roster Strength)...")
    # 現在我們有 (gameId, teamId)，可以直接聚合了
    match_impact = df_players.groupby(['gameId', 'teamId'])['player_season_impact'].sum().reset_index()
    match_impact.rename(columns={'player_season_impact': 'roster_impact_score'}, inplace=True)
    
    # 存檔
    output_path = 'data/match_roster_impact.csv'
    match_impact.to_csv(output_path, index=False)
    print(f"✅ 成功！已建立 {output_path}")
    print("   欄位包含: gameId, teamId, roster_impact_score")
    print("   現在可以直接被 train_model.py 讀取並合併了！")

if __name__ == "__main__":
    if not os.path.exists('data/PlayerStatistics.csv'):
        print("❌ 錯誤: 找不到 data/PlayerStatistics.csv")
    else:
        process_player_impact()