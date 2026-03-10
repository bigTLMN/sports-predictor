import pandas as pd
import joblib
import os
import numpy as np

# NBA 隊名轉 ID (跟 build_player_features.py 保持一致)
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

def export_data():
    print("🔄 讀取球員歷史數據 (PlayerStatistics.csv)...")
    
    if not os.path.exists('data/PlayerStatistics.csv'):
        print("❌ 錯誤: 找不到 data/PlayerStatistics.csv")
        return

    # 只讀需要的欄位
    cols = ['gameDateTimeEst', 'points', 'fieldGoalsMade', 'fieldGoalsAttempted', 
            'freeThrowsMade', 'freeThrowsAttempted', 'reboundsOffensive', 'reboundsDefensive', 
            'steals', 'assists', 'blocks', 'foulsPersonal', 'turnovers', 
            'playerteamName', 'firstName', 'lastName']
    
    df = pd.read_csv('data/PlayerStatistics.csv', usecols=lambda c: c in cols, low_memory=False)
    
    # 🔥 修正：分開處理缺失值，避免型別錯誤
    
    # 1. 數值欄位填 0
    numeric_cols = ['points', 'fieldGoalsMade', 'fieldGoalsAttempted', 
            'freeThrowsMade', 'freeThrowsAttempted', 'reboundsOffensive', 'reboundsDefensive', 
            'steals', 'assists', 'blocks', 'foulsPersonal', 'turnovers']
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    # 2. 字串欄位填空字串，並強制轉為 string
    str_cols = ['firstName', 'lastName', 'playerteamName']
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)

    # 計算單場 GameScore
    print("   計算戰力值 (GameScore)...")
    def calc_gm_score(row):
        try:
            return (row['points'] + 0.4 * row['fieldGoalsMade'] - 0.7 * row['fieldGoalsAttempted'] - 
                    0.4 * (row['freeThrowsAttempted'] - row['freeThrowsMade']) + 0.7 * row['reboundsOffensive'] + 
                    0.3 * row['reboundsDefensive'] + row['steals'] + 0.7 * row['assists'] + 
                    0.7 * row['blocks'] - 0.4 * row['foulsPersonal'] - row['turnovers'])
        except:
            return 0

    df['gm_score'] = df.apply(calc_gm_score, axis=1)
    
    # 組全名 (用來對應傷兵名單)
    df['fullName'] = df['firstName'] + ' ' + df['lastName']
    
    # 篩選最近數據 (例如最近 90 天)，以反映「本季」狀態
    # 先把沒有日期的資料刪掉
    df = df.dropna(subset=['gameDateTimeEst'])
    df['gameDateTimeEst'] = pd.to_datetime(df['gameDateTimeEst'])
    
    if df.empty:
        print("❌ 錯誤: 資料集為空或日期格式錯誤")
        return

    latest_date = df['gameDateTimeEst'].max()
    start_date = latest_date - pd.Timedelta(days=90) 
    
    print(f"   篩選近期數據 ({start_date.date()} ~ {latest_date.date()})...")
    df_recent = df[df['gameDateTimeEst'] >= start_date].copy()
    
    # 1. 建立球員戰力表 (Player Impact Map)
    # 取平均值
    player_impact = df_recent.groupby('fullName')['gm_score'].mean().to_dict()
    
    # 2. 建立球隊完整名單 (Team Roster)
    # 轉換隊名為 ID
    df_recent['teamId'] = df_recent['playerteamName'].map(TEAM_NAME_TO_ID)
    df_recent = df_recent.dropna(subset=['teamId'])
    df_recent['teamId'] = df_recent['teamId'].astype(int)
    
    team_rosters = {}
    
    print("   建立球隊輪替名單...")
    for team_id in df_recent['teamId'].unique():
        team_players = df_recent[df_recent['teamId'] == team_id]
        # 根據總戰力排序，取前 15 人作為 "Active Roster"
        top_players = team_players.groupby('fullName')['gm_score'].sum().sort_values(ascending=False).head(15).index.tolist()
        team_rosters[int(team_id)] = top_players
    
    # 存檔 (存到根目錄)
    print("💾 儲存至根目錄...")
    joblib.dump(player_impact, 'player_impact_map.pkl')
    joblib.dump(team_rosters, 'team_rosters.pkl')
    
    print(f"✅ 成功匯出戰力資料！")
    print(f"   - 球員戰力表: player_impact_map.pkl")
    print(f"   - 球隊名單: team_rosters.pkl")

if __name__ == "__main__":
    export_data()