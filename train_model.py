import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_absolute_error
import joblib
import os

# ==========================================
# 1. 定義特徵欄位
# ==========================================
RAW_FEATURES = [
    'fieldGoalsPercentage', 'threePointersPercentage', 'freeThrowsPercentage',
    'reboundsTotal', 'assists', 'steals', 'blocks', 'turnovers', 
    'plusMinusPoints', 'pointsInThePaint', 'teamScore' # 保留用來計算 Target，但不放入 X
]

# 訓練用的特徵 (已移除 teamScore)
TRAIN_FEATURES_SPREAD = [
    'is_home', 
    'diff_fieldGoalsPercentage', 'diff_threePointersPercentage', 'diff_freeThrowsPercentage',
    'diff_reboundsTotal', 'diff_assists', 'diff_steals', 'diff_blocks', 'diff_turnovers',
    'diff_plusMinusPoints', 'diff_pointsInThePaint'
]

TRAIN_FEATURES_TOTAL = [
    'sum_fieldGoalsPercentage', 'sum_threePointersPercentage', 'sum_freeThrowsPercentage',
    'sum_reboundsTotal', 'sum_assists', 'sum_steals', 'sum_blocks', 'sum_turnovers',
    'sum_plusMinusPoints', 'sum_pointsInThePaint'
]

def load_and_clean_data():
    print("📂 [V3] 正在讀取 TeamStatistics.csv ...")
    try:
        # 只讀取需要的欄位
        cols = ['gameId', 'teamId', 'gameDateTimeEst', 'home', 'win', 'teamScore', 'opponentScore'] + RAW_FEATURES
        df = pd.read_csv('data/TeamStatistics.csv', usecols=cols, low_memory=False)

        # 🔥🔥🔥 關鍵修正：移除 format='mixed' 以支援 Python 3.7 🔥🔥🔥
        # 舊版 Pandas 會自動偵測 ISO8601 格式，不需要指定 format
        df['gameDateTimeEst'] = pd.to_datetime(df['gameDateTimeEst'], utc=True, errors='coerce')
        
        # 檢查無效日期
        invalid_count = df['gameDateTimeEst'].isnull().sum()
        if invalid_count > 0:
            print(f"   ⚠️ Warning: 發現 {invalid_count} 筆無效日期，已自動過濾。")
            df = df.dropna(subset=['gameDateTimeEst'])
        
        # 檢查是否還有資料
        if df.empty:
            print("❌ 錯誤：所有日期解析失敗，DataFrame 為空！請檢查 TeamStatistics.csv 的日期格式。")
            exit()

        # 排序
        df = df.sort_values(['teamId', 'gameDateTimeEst'])
        
        # 滾動平均 (Rolling Average) - 計算近 5 場表現
        df_rolled = df.groupby('teamId', group_keys=False)[RAW_FEATURES].apply(lambda x: x.shift(1).rolling(5, min_periods=1).mean())
        
        # 把原始資訊接回來
        for col in ['gameId', 'gameDateTimeEst', 'home', 'win', 'teamScore', 'opponentScore']:
            df_rolled[col] = df[col]
            
        # 移除前幾場沒有滾動數據的行
        df_rolled = df_rolled.dropna()
        
        return df_rolled

    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
        exit()

def prepare_training_data(df):
    print("🔄 [V3] 特徵工程：計算 Diff (讓分用) 與 Sum (大小分用)...")
    
    df_home = df[df['home'] == 1].copy()
    df_away = df[df['home'] == 0].copy()
    
    merged = pd.merge(df_home, df_away, on='gameId', suffixes=('_h', '_a'))
    
    merged['is_home'] = 1 
    
    for col in RAW_FEATURES:
        merged[f'diff_{col}'] = merged[f'{col}_h'] - merged[f'{col}_a']
        merged[f'sum_{col}'] = merged[f'{col}_h'] + merged[f'{col}_a']
        
    merged['target_win'] = merged['win_h'] 
    merged['target_margin'] = merged['teamScore_h'] - merged['teamScore_a']
    merged['target_total'] = merged['teamScore_h'] + merged['teamScore_a']
    
    return merged

def train():
    df = load_and_clean_data()
    
    # 再次檢查資料量
    if len(df) < 10:
        print(f"❌ 資料量過少 ({len(df)} 筆)，無法訓練。")
        exit()

    data = prepare_training_data(df)
    
    # --- 模型 1: 勝負預測 ---
    print("\n🤖 訓練模型 1: 勝負預測 (Win/Loss)...")
    X_win = data[TRAIN_FEATURES_SPREAD]
    y_win = data['target_win']
    
    X_train, X_test, y_train, y_test = train_test_split(X_win, y_win, test_size=0.2, random_state=42)
    model_win = xgb.XGBClassifier(use_label_encoder=False, eval_metric='logloss')
    model_win.fit(X_train, y_train)
    
    preds = model_win.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"   🎯 勝率準確度: {acc*100:.2f}%")
    
    # --- 模型 2: 讓分預測 ---
    print("\n🤖 訓練模型 2: 讓分預測 (Spread Margin)...")
    X_spread = data[TRAIN_FEATURES_SPREAD]
    y_spread = data['target_margin']
    
    X_train, X_test, y_train, y_test = train_test_split(X_spread, y_spread, test_size=0.2, random_state=42)
    model_spread = xgb.XGBRegressor(objective='reg:squarederror')
    model_spread.fit(X_train, y_train)
    
    preds = model_spread.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    print(f"   📏 平均誤差 (MAE): {mae:.2f} 分 (越低越好)")
    
    # --- 模型 3: 大小分預測 ---
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
    joblib.dump(TRAIN_FEATURES_SPREAD, 'features_spread.pkl')
    joblib.dump(TRAIN_FEATURES_TOTAL, 'features_total.pkl')
    
    print("\n💾 所有模型與特徵已儲存完畢！")

if __name__ == "__main__":
    train()