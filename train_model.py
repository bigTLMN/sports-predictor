import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score, mean_absolute_error
import joblib
import numpy as np

# ==========================================
# 1. 定義特徵欄位
# ==========================================
RAW_FEATURES = [
    'fieldGoalsPercentage', 'threePointersPercentage', 'freeThrowsPercentage',
    'reboundsTotal', 'assists', 'steals', 'blocks', 'turnovers', 
    'plusMinusPoints', 'pointsInThePaint', 'teamScore', # 平均得分
    'eFG_Percentage', 'TS_Percentage', 'RestDays' 
]

TRAIN_FEATURES_SPREAD = [
    'is_home', 
    'diff_fieldGoalsPercentage', 'diff_threePointersPercentage', 'diff_freeThrowsPercentage',
    'diff_reboundsTotal', 'diff_assists', 'diff_steals', 'diff_blocks', 'diff_turnovers',
    'diff_plusMinusPoints', 'diff_pointsInThePaint', 'diff_teamScore',
    'diff_eFG_Percentage', 'diff_TS_Percentage', 'diff_RestDays'
]

TRAIN_FEATURES_TOTAL = [
    'sum_fieldGoalsPercentage', 'sum_threePointersPercentage', 'sum_freeThrowsPercentage',
    'sum_reboundsTotal', 'sum_assists', 'sum_steals', 'sum_blocks', 'sum_turnovers',
    'sum_plusMinusPoints', 'sum_pointsInThePaint', 'sum_teamScore',
    'sum_eFG_Percentage', 'sum_TS_Percentage', 'sum_RestDays'
]

# ==========================================
# 🔥 V7 黃金參數設定 (來自 Optuna 調優結果)
# ==========================================
# 準確率: 61.31%
BEST_PARAMS_WIN = {
    'n_estimators': 718,
    'max_depth': 5,
    'learning_rate': 0.03533961656438241,
    'subsample': 0.6484503588896959,
    'colsample_bytree': 0.9632952080248166,
    'gamma': 2.939906293582819,
    'reg_alpha': 8.560976029412572,
    'reg_lambda': 1.2370734727589927,
    'eval_metric': 'logloss',
    'missing': np.nan,
    'n_jobs': -1  # 使用所有 CPU 核心加速
}

# MAE: 11.30
BEST_PARAMS_SPREAD = {
    'n_estimators': 402,
    'max_depth': 4,
    'learning_rate': 0.03829740791851101,
    'subsample': 0.8738053260924176,
    'colsample_bytree': 0.6875150549185579,
    'gamma': 3.094541066333537,
    'reg_alpha': 8.798248214325517,
    'reg_lambda': 4.352142926938036,
    'objective': 'reg:squarederror',
    'missing': np.nan,
    'n_jobs': -1
}

# MAE: 15.32
BEST_PARAMS_TOTAL = {
    'n_estimators': 260,
    'max_depth': 3,
    'learning_rate': 0.048704903844645306,
    'subsample': 0.7019618661196612,
    'colsample_bytree': 0.887010784767337,
    'gamma': 2.3825596062902483,
    'reg_alpha': 5.267017175798149,
    'reg_lambda': 4.245952737001013,
    'objective': 'reg:squarederror',
    'missing': np.nan,
    'n_jobs': -1
}

def load_and_clean_data():
    print("📂 [V7] 正在讀取 TeamStatistics.csv (黃金參數版)...")
    try:
        # 1. 讀取數據
        req_cols = [
            'gameId', 'teamId', 'gameDateTimeEst', 'home', 'win', 'teamScore', 'opponentScore',
            'fieldGoalsMade', 'fieldGoalsAttempted', 'threePointersMade', 
            'freeThrowsAttempted',
            'fieldGoalsPercentage', 'threePointersPercentage', 'freeThrowsPercentage',
            'reboundsTotal', 'assists', 'steals', 'blocks', 'turnovers', 
            'plusMinusPoints', 'pointsInThePaint'
        ]
        
        df = pd.read_csv('data/TeamStatistics.csv', usecols=lambda c: c in req_cols, low_memory=False)

        # 2. 日期處理
        df['gameDateTimeEst'] = df['gameDateTimeEst'].astype(str).str.slice(0, 10)
        df['gameDateTimeEst'] = pd.to_datetime(df['gameDateTimeEst'], utc=True, errors='coerce')
        df = df.dropna(subset=['gameDateTimeEst'])
        
        if df.empty:
            print("❌ 錯誤：DataFrame 為空！")
            exit()

        # 3. 排序
        df = df.sort_values(['teamId', 'gameDateTimeEst'])
        
        # 4. 特徵工程
        df['threePointersMade'] = df['threePointersMade'].fillna(0)
        df['fieldGoalsAttempted'] = df['fieldGoalsAttempted'].replace(0, np.nan)
        
        df['eFG_Percentage'] = (df['fieldGoalsMade'] + 0.5 * df['threePointersMade']) / df['fieldGoalsAttempted']
        df['TS_Percentage'] = df['teamScore'] / (2 * (df['fieldGoalsAttempted'] + 0.44 * df['freeThrowsAttempted']))
        
        df['eFG_Percentage'] = df['eFG_Percentage'].fillna(0)
        df['TS_Percentage'] = df['TS_Percentage'].fillna(0)

        df['prev_game_date'] = df.groupby('teamId')['gameDateTimeEst'].shift(1)
        df['RestDays'] = (df['gameDateTimeEst'] - df['prev_game_date']).dt.days
        df['RestDays'] = df['RestDays'].fillna(3).clip(upper=7)

        # 5. 滾動平均
        print("   🔄 執行滾動平均計算...")
        cols_to_roll = [c for c in RAW_FEATURES if c in df.columns]
        
        df_rolled = df.groupby('teamId', group_keys=False)[cols_to_roll].apply(
            lambda x: x.shift(1).rolling(5, min_periods=1).mean()
        )
        
        # 6. 合併
        meta_cols = ['gameId', 'gameDateTimeEst', 'home', 'win', 'teamScore', 'opponentScore']
        df_meta = df[meta_cols].rename(columns={
            'teamScore': 'actual_teamScore', 
            'opponentScore': 'actual_opponentScore'
        })
        
        df_final = pd.concat([df_meta, df_rolled], axis=1)
        
        # 7. 最終過濾
        df_final = df_final.dropna(subset=['win', 'actual_teamScore', 'actual_opponentScore'])
        
        print(f"   ✅ 資料處理完成！最終有效訓練行數: {len(df_final)}")
        return df_final

    except Exception as e:
        import traceback
        print(f"❌ 發生錯誤: {e}")
        traceback.print_exc()
        exit()

def prepare_training_data(df):
    print(f"🔄 [V7] 正在準備對戰組合 ({len(df)} rows)...")
    
    df_home = df[df['home'] == 1].copy()
    df_away = df[df['home'] == 0].copy()
    
    merged = pd.merge(df_home, df_away, on='gameId', suffixes=('_h', '_a'))
    merged = merged.sort_values('gameDateTimeEst_h')
    
    merged['is_home'] = 1 
    
    for col in RAW_FEATURES:
        if f'{col}_h' not in merged.columns or f'{col}_a' not in merged.columns:
            continue
            
        merged[f'diff_{col}'] = merged[f'{col}_h'] - merged[f'{col}_a']
        merged[f'sum_{col}'] = merged[f'{col}_h'] + merged[f'{col}_a']
    
    merged['target_win'] = merged['win_h'] 
    merged['target_margin'] = merged['actual_teamScore_h'] - merged['actual_teamScore_a']
    merged['target_total'] = merged['actual_teamScore_h'] + merged['actual_teamScore_a']
    
    return merged

def train():
    df = load_and_clean_data()
    
    if len(df) < 50:
        print(f"❌ 資料量過少，無法訓練。")
        exit()

    data = prepare_training_data(df)
    
    # 時間序列切分
    split_idx = int(len(data) * 0.85)
    train_data = data.iloc[:split_idx]
    test_data = data.iloc[split_idx:]
    
    print(f"\n📅 訓練區間: {train_data['gameDateTimeEst_h'].min().date()} ~ {train_data['gameDateTimeEst_h'].max().date()}")
    print(f"📅 驗證區間: {test_data['gameDateTimeEst_h'].min().date()} ~ {test_data['gameDateTimeEst_h'].max().date()}")
    
    # 動態特徵選擇
    available_features_spread = [f for f in TRAIN_FEATURES_SPREAD if f in data.columns]
    available_features_total = [f for f in TRAIN_FEATURES_TOTAL if f in data.columns]
    
    # --- 模型 1: 勝負預測 (使用黃金參數) ---
    print("\n🤖 訓練模型 1: 勝負預測 (Win/Loss)...")
    # 🔥 載入 BEST_PARAMS_WIN
    model_win = xgb.XGBClassifier(**BEST_PARAMS_WIN)
    model_win.fit(train_data[available_features_spread], train_data['target_win'])
    
    acc = accuracy_score(test_data['target_win'], model_win.predict(test_data[available_features_spread]))
    print(f"   🎯 V7 最終回測準確度: {acc*100:.2f}% (Target: >60%)")
    
    # --- 模型 2: 讓分預測 (使用黃金參數) ---
    print("\n🤖 訓練模型 2: 讓分預測 (Spread Margin)...")
    # 🔥 載入 BEST_PARAMS_SPREAD
    model_spread = xgb.XGBRegressor(**BEST_PARAMS_SPREAD)
    model_spread.fit(train_data[available_features_spread], train_data['target_margin'])
    
    mae = mean_absolute_error(test_data['target_margin'], model_spread.predict(test_data[available_features_spread]))
    print(f"   📏 平均誤差 (MAE): {mae:.2f} 分")
    
    # --- 模型 3: 大小分預測 (使用黃金參數) ---
    print("\n🤖 訓練模型 3: 大小分預測 (Total Points)...")
    # 🔥 載入 BEST_PARAMS_TOTAL
    model_total = xgb.XGBRegressor(**BEST_PARAMS_TOTAL)
    model_total.fit(train_data[available_features_total], train_data['target_total'])
    
    mae = mean_absolute_error(test_data['target_total'], model_total.predict(test_data[available_features_total]))
    print(f"   📏 平均誤差 (MAE): {mae:.2f} 分")
    
    # --- 儲存 ---
    joblib.dump(model_win, 'model_win.pkl')
    joblib.dump(model_spread, 'model_spread.pkl')
    joblib.dump(model_total, 'model_total.pkl')
    joblib.dump(available_features_spread, 'features_spread.pkl')
    joblib.dump(available_features_total, 'features_total.pkl')
    
    print("\n💾 V7 模型訓練完成！所有系統已就緒。")

if __name__ == "__main__":
    train()