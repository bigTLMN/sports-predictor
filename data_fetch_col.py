import pandas as pd

# 讀取 CSV
try:
    games = pd.read_csv('data/Games.csv')
    stats = pd.read_csv('data/TeamStatistics.csv')

    print("=== Games.csv Columns ===")
    print(games.columns.tolist())
    print(games.head(1)) # 印第一行看一下資料長相

    print("\n=== TeamStatistics.csv Columns ===")
    print(stats.columns.tolist())
    print(stats.head(1))
except Exception as e:
    print(f"讀取失敗: {e}")