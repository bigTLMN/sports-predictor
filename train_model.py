import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_absolute_error
import joblib
import os

# ==========================================
# 1. 定義特徵欄位 (必須與 aggregate_picks.py 一致)
# ==========================================
RAW_FEATURES = [
    'fieldGoalsPercentage', 'threePointersPercentage', 'freeThrowsPercentage',
    'reboundsTotal', 'assists', 'steals', 'blocks', 'turnovers', 
    'plusMinusPoints', 'pointsInThePaint', 'teamScore'
]

# 這些是經過特徵工程後，真正餵給模型訓練的欄位
TRAIN_FEATURES_SPREAD = [
    'is_home', 
    'diff_fieldGoalsPercentage', 'diff_threePointersPercentage', 'diff_freeThrowsPercentage',
    'diff_reboundsTotal', 'diff_assists', 'diff_steals', 'diff_blocks', 'diff_turnovers',
    'diff_plusMinusPoints', 'diff_pointsInThePaint', 'diff_teamScore'
]

TRAIN_FEATURES_TOTAL = [
    'sum_fieldGoalsPercentage', 'sum_threePointersPercentage', 'sum_freeThrowsPercentage',
    'sum_reboundsTotal', 'sum_assists', 'sum_steals', 'sum_blocks', 'sum_turnovers',
    'sum_plusMinusPoints', 'sum_pointsInThePaint', 'sum_teamScore'
]

def load_and_clean_data():
    print("📂 [V3] 正在讀取 TeamStatistics.csv ...")
    try:
        # 只讀取需要的欄位
        cols = ['gameId', 'teamId', 'gameDateTimeEst', 'home', 'win', 'teamScore', 'opponentScore'] + RAW_FEATURES
        df = pd.read_csv('data/TeamStatistics.csv', usecols=cols, low_memory=False)

        # 🔥🔥🔥 關鍵修正：強壯的日期解析 (Fix Date Parsing Error) 🔥🔥🔥
        # 使用 format='mixed' 讓它自動處理 ISO8601 和帶時區的格式
        # errors='coerce' 會把無法解析的變成 NaT，避免 crash
        df['gameDateTimeEst'] = pd.to_datetime(df['gameDateTimeEst'], utc=True, format='mixed', errors='coerce')
        
        # 移除無效日期的資料
        if df['gameDateTimeEst'].isnull().any():
            print(f"   ⚠️ Warning: 發現 {df['gameDateTimeEst'].isnull().sum()} 筆無效日期，已自動過濾。")
            df = df.dropna(subset=['gameDateTimeEst'])

        # 排序
        df = df.sort_values(['teamId', 'gameDateTimeEst'])
        
        # 滾動平均 (Rolling Average) - 計算近 5 場表現
        # group_keys=False 避免索引層級增加
        df_rolled = df.groupby('teamId', group_keys=False)[RAW_FEATURES].apply(lambda x: x.shift(1).rolling(5, min_periods=1).mean())
        
        # 把原始資訊 (gameId, date, score...) 接回來
        for col in ['gameId', 'gameDateTimeEst', 'home', 'win', 'teamScore', 'opponentScore']:
            df_rolled[col] = df[col]
            
        # 移除沒有滾動數據的前幾場 (NaN)
        df_rolled = df_rolled.dropna()
        
        return df_rolled

    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
        exit()

def prepare_training_data(df):
    print("🔄 [V3] 特徵工程：計算 Diff (讓分用) 與 Sum (大小分用)...")
    
    # 自行 Join：把同一場比賽的主客隊數據併在同一列
    # 1. 分出主隊與客隊
    df_home = df[df['home'] == 1].copy()
    df_away = df[df['home'] == 0].copy()
    
    # 2. 合併 (Merge)
    merged = pd.merge(df_home, df_away, on='gameId', suffixes=('_h', '_a'))
    
    # 3. 產生特徵
    merged['is_home'] = 1 
    
    # 計算 Diff (主隊 - 客隊) -> 用於預測勝負/讓分
    for col in RAW_FEATURES:
        merged[f'diff_{col}'] = merged[f'{col}_h'] - merged[f'{col}_a']
        
    # 計算 Sum (主隊 + 客隊) -> 用於預測大小分
    for col in RAW_FEATURES:
        merged[f'sum_{col}'] = merged[f'{col}_h'] + merged[f'{col}_a']
        
    # 定義 Target (目標值)
    # Win: 主隊贏=1, 輸=0
    merged['target_win'] = merged['win_h'] 
    
    # Spread: 主隊贏分 (例如 +5 或 -10)
    merged['target_margin'] = merged['teamScore_h'] - merged['teamScore_a']
    
    # Total: 總分
    merged['target_total'] = merged['teamScore_h'] + merged['teamScore_a']
    
    return merged

def train():
    df = load_and_clean_data()
    data = prepare_training_data(df)
    
    # --- 模型 1: 勝負預測 (Classification) ---
    print("\n🤖 訓練模型 1: 勝負預測 (Win/Loss)...")
    X_win = data[TRAIN_FEATURES_SPREAD]
    y_win = data['target_win']
    
    X_train, X_test, y_train, y_test = train_test_split(X_win, y_win, test_size=0.2, random_state=42)
    model_win = xgb.XGBClassifier(use_label_encoder=False, eval_metric='logloss')
    model_win.fit(X_train, y_train)
    
    preds = model_win.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"   🎯 勝率準確度: {acc*100:.2f}%")
    
    # --- 模型 2: 讓分預測 (Regression) ---
    print("\n🤖 訓練模型 2: 讓分預測 (Spread Margin)...")
    X_spread = data[TRAIN_FEATURES_SPREAD]
    y_spread = data['target_margin']
    
    X_train, X_test, y_train, y_test = train_test_split(X_spread, y_spread, test_size=0.2, random_state=42)
    model_spread = xgb.XGBRegressor(objective='reg:squarederror')
    model_spread.fit(X_train, y_train)
    
    preds = model_spread.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    print(f"   📏 平均誤差 (MAE): {mae:.2f} 分 (越低越好)")
    
    # --- 模型 3: 大小分預測 (Regression) ---
    print("\n🤖 訓練模型 3: 大小分預測 (Total Points)...")
    X_total = data[TRAIN_FEATURES_TOTAL]
    y_total = data['target_total']
    
    X_train, X_test, y_train, y_test = train_test_split(X_total, y_total, test_size=0.2, random_state=42)
    model_total = xgb.XGBRegressor(objective='reg:squarederror')
    model_total.fit(X_train, y_train)
    
    preds = model_total.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    print(f"   📏 平均誤差 (MAE): {mae:.2f} 分")
    
    # --- 儲存模型 ---
    joblib.dump(model_win, 'model_win.pkl')
    joblib.dump(model_spread, 'model_spread.pkl')
    joblib.dump(model_total, 'model_total.pkl')
    # 儲存特徵列表，確保預測時欄位順序一致
    joblib.dump(TRAIN_FEATURES_SPREAD, 'features_spread.pkl')
    joblib.dump(TRAIN_FEATURES_TOTAL, 'features_total.pkl')
    
    print("\n💾 所有模型與特徵已儲存完畢！")

if __name__ == "__main__":
    train()