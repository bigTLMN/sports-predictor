import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score, mean_absolute_error
from sklearn.ensemble import VotingClassifier, VotingRegressor # 🔥 集成學習模組
import joblib
import numpy as np
import os

# ==========================================
# 1. 定義特徵欄位 (動態生成)
# ==========================================
# 基礎數據 (Raw Stats)
BASE_STATS_COLS = [
    'fieldGoalsPercentage', 'threePointersPercentage', 'freeThrowsPercentage',
    'reboundsTotal', 'assists', 'steals', 'blocks', 'turnovers', 
    'plusMinusPoints', 'pointsInThePaint', 'teamScore', 
    'eFG_Percentage', 'TS_Percentage', 'RestDays',
    'roster_impact_score' # 🔥 新增：陣容強度分數
]

# 定義多重時間窗口
ROLLING_WINDOWS = [5, 10, 30] 

# 動態生成訓練特徵列表
TRAIN_FEATURES_SPREAD = ['is_home'] 
TRAIN_FEATURES_TOTAL = []

for w in ROLLING_WINDOWS:
    for col in BASE_STATS_COLS:
        TRAIN_FEATURES_SPREAD.append(f'diff_rolling_{w}_{col}')
        TRAIN_FEATURES_TOTAL.append(f'sum_rolling_{w}_{col}')
    
    # 加入勝率
    TRAIN_FEATURES_SPREAD.append(f'diff_rolling_{w}_win_rate')
    TRAIN_FEATURES_TOTAL.append(f'sum_rolling_{w}_win_rate')

# 🔥 新增：陣容完整度與缺損特徵 (不依賴 rolling，而是當場差異)
TRAIN_FEATURES_SPREAD.append('diff_roster_impact')    # 雙方今日陣容強度差
TRAIN_FEATURES_SPREAD.append('diff_missing_impact')   # 雙方「戰力缺損」差 (最重要！)

# ==========================================
# 🔥 V8.0 黃金參數設定 (來自 Optuna 2026/01/29 調優結果)
# ==========================================
# 準確率: 64.84%
BEST_PARAMS_WIN = {
    'n_estimators': 509,
    'max_depth': 3,
    'learning_rate': 0.043041813813351315,
    'subsample': 0.9183040925737341,
    'colsample_bytree': 0.8256708824079241,
    'gamma': 2.6374110720253743,
    'reg_alpha': 4.528441834346028,
    'reg_lambda': 5.724831419033642,
    'eval_metric': 'logloss',
    'missing': np.nan,
    'n_jobs': 1 # 🔥 改為 1，因為 Voting 會平行處理多個模型，避免 CPU 搶佔
}

# MAE: 11.38
BEST_PARAMS_SPREAD = {
    'n_estimators': 150,
    'max_depth': 3,
    'learning_rate': 0.06353984448063979,
    'subsample': 0.7960172713384834,
    'colsample_bytree': 0.5336338509404283,
    'gamma': 1.6885593428727688,
    'reg_alpha': 0.823932964710099,
    'reg_lambda': 9.364714111214916,
    'objective': 'reg:squarederror',
    'missing': np.nan,
    'n_jobs': 1 
}

# MAE: 15.10
BEST_PARAMS_TOTAL = {
    'n_estimators': 582,
    'max_depth': 3,
    'learning_rate': 0.01207095656064304,
    'subsample': 0.5202392305925475,
    'colsample_bytree': 0.7328987553300463,
    'gamma': 4.3526803881390705,
    'reg_alpha': 5.14487112629654,
    'reg_lambda': 4.892385537038124,
    'objective': 'reg:squarederror',
    'missing': np.nan,
    'n_jobs': 1
}

def load_and_clean_data():
    print("📂 [V9.5] 正在讀取 TeamStatistics.csv (含 Roster Impact)...")
    try:
        # 1. 讀取基礎數據
        req_cols = [
            'gameId', 'teamId', 'gameDateTimeEst', 'home', 'win', 'teamScore', 'opponentScore',
            'fieldGoalsMade', 'fieldGoalsAttempted', 'threePointersMade', 
            'freeThrowsAttempted',
            'fieldGoalsPercentage', 'threePointersPercentage', 'freeThrowsPercentage',
            'reboundsTotal', 'assists', 'steals', 'blocks', 'turnovers', 
            'plusMinusPoints', 'pointsInThePaint'
        ]
        
        df = pd.read_csv('data/TeamStatistics.csv', usecols=lambda c: c in req_cols, low_memory=False)
        df['gameId'] = df['gameId'].astype(str) # 統一轉字串

        # 2. 🔥 合併 Roster Impact (球員影響力)
        if os.path.exists('data/match_roster_impact.csv'):
            print("   🔗 合併球員影響力特徵 (match_roster_impact.csv)...")
            df_impact = pd.read_csv('data/match_roster_impact.csv')
            df_impact['gameId'] = df_impact['gameId'].astype(str)
            
            # Left Join
            df = pd.merge(df, df_impact, on=['gameId', 'teamId'], how='left')
            
            # 填補遺失值 (如果是舊比賽沒數據，填補平均值)
            df['roster_impact_score'] = df['roster_impact_score'].fillna(df['roster_impact_score'].mean())
        else:
            print("⚠️ 警告: 找不到 match_roster_impact.csv，請先執行 build_player_features.py")
            df['roster_impact_score'] = 0

        # 3. 日期處理
        df['gameDateTimeEst'] = df['gameDateTimeEst'].astype(str).str.slice(0, 10)
        df['gameDateTimeEst'] = pd.to_datetime(df['gameDateTimeEst'], utc=True, errors='coerce')
        df = df.dropna(subset=['gameDateTimeEst'])
        
        # Concept Drift 修正
        CUTOFF_YEAR = 2015
        print(f"✂️ [Concept Drift Fix] 過濾數據：僅保留 {CUTOFF_YEAR} 年以後的現代籃球數據...")
        df = df[df['gameDateTimeEst'].dt.year >= CUTOFF_YEAR]
        
        # 4. 排序 (重要)
        df = df.sort_values(['teamId', 'gameDateTimeEst'])

        # 修正：移除 'win' 為 NaN 的資料
        if df['win'].isnull().any():
            print(f"   ⚠️ 發現 {df['win'].isnull().sum()} 筆無勝負結果的資料(可能是未來賽程)，已移除。")
            df = df.dropna(subset=['win'])

        # 5. 特徵工程
        df['threePointersMade'] = df['threePointersMade'].fillna(0)
        df['fieldGoalsAttempted'] = df['fieldGoalsAttempted'].replace(0, np.nan)
        
        df['eFG_Percentage'] = (df['fieldGoalsMade'] + 0.5 * df['threePointersMade']) / df['fieldGoalsAttempted']
        df['TS_Percentage'] = df['teamScore'] / (2 * (df['fieldGoalsAttempted'] + 0.44 * df['freeThrowsAttempted']))
        df['eFG_Percentage'] = df['eFG_Percentage'].fillna(0)
        df['TS_Percentage'] = df['TS_Percentage'].fillna(0)

        df['prev_game_date'] = df.groupby('teamId')['gameDateTimeEst'].shift(1)
        df['RestDays'] = (df['gameDateTimeEst'] - df['prev_game_date']).dt.days
        df['RestDays'] = df['RestDays'].fillna(3).clip(upper=7)
        
        df['win_numeric'] = df['win'].astype(int)

        # 6. 滾動平均
        print("   🔄 執行多重滾動平均計算 (Windows: 5, 10, 30)...")
        
        cols_to_roll = [c for c in BASE_STATS_COLS if c in df.columns and c != 'RestDays']
        cols_to_roll.append('RestDays')
        
        # 確保 roster_impact_score 在滾動列表裡
        if 'roster_impact_score' not in cols_to_roll and 'roster_impact_score' in df.columns:
            cols_to_roll.append('roster_impact_score')
        
        for w in ROLLING_WINDOWS:
            # 6.1 計算數據統計平均
            rolled_stats = df.groupby('teamId', group_keys=False)[cols_to_roll].apply(
                lambda x: x.shift(1).rolling(w, min_periods=1).mean()
            )
            rolled_stats.columns = [f'rolling_{w}_{c}' for c in rolled_stats.columns]
            
            # 6.2 計算勝率 (Win Rate)
            rolled_win = df.groupby('teamId', group_keys=False)['win_numeric'].apply(
                lambda x: x.shift(1).rolling(w, min_periods=1).mean()
            )
            rolled_stats[f'rolling_{w}_win_rate'] = rolled_win
            
            # 6.3 合併回主表
            df = pd.concat([df, rolled_stats], axis=1)
        
        # 7. 清理與過濾
        meta_cols = ['gameId', 'gameDateTimeEst', 'home', 'win', 'teamScore', 'opponentScore', 'roster_impact_score']
        keep_cols = meta_cols + [c for c in df.columns if 'rolling_' in c]
        
        df_final = df[keep_cols].rename(columns={
            'teamScore': 'actual_teamScore', 
            'opponentScore': 'actual_opponentScore'
        })
        
        df_final = df_final.dropna(subset=['win', 'actual_teamScore', 'actual_opponentScore'])
        
        print(f"   ✅ 資料處理完成！總行數: {len(df_final)}")
        return df_final

    except Exception as e:
        import traceback
        print(f"❌ 發生錯誤: {e}")
        traceback.print_exc()
        exit()

def prepare_training_data(df):
    print(f"🔄 [V9.5] 準備對戰特徵...")
    
    df_home = df[df['home'] == 1].copy()
    df_away = df[df['home'] == 0].copy()
    
    merged = pd.merge(df_home, df_away, on='gameId', suffixes=('_h', '_a'))
    merged = merged.sort_values('gameDateTimeEst_h')
    
    merged['is_home'] = 1 
    
    # 自動計算 Diff 和 Sum
    needed_features = set()
    for f in TRAIN_FEATURES_SPREAD:
        if f.startswith('diff_') and 'roster' not in f and 'missing' not in f:
            needed_features.add(f.replace('diff_', ''))
            
    for base_col in needed_features:
        h_col = f"{base_col}_h"
        a_col = f"{base_col}_a"
        
        if h_col in merged.columns and a_col in merged.columns:
            merged[f'diff_{base_col}'] = merged[h_col] - merged[a_col]
            merged[f'sum_{base_col}'] = merged[h_col] + merged[a_col]

    # 🔥🔥 計算陣容強度相關特徵 (V9.0 新增) 🔥🔥
    # 1. 直接比較雙方今日強度 (主隊強度 - 客隊強度)
    if 'roster_impact_score_h' in merged.columns:
        merged['diff_roster_impact'] = merged['roster_impact_score_h'] - merged['roster_impact_score_a']
        
        # 2. 比較「戰力缺損程度」 (Missing Impact)
        # 今日強度 - 近10場平均強度 (如果 < 0 代表今日戰力比平常差)
        merged['missing_impact_h'] = merged['roster_impact_score_h'] - merged['rolling_10_roster_impact_score_h']
        merged['missing_impact_a'] = merged['roster_impact_score_a'] - merged['rolling_10_roster_impact_score_a']
        
        # 3. 雙方缺損差異 (主隊缺損 - 客隊缺損)
        merged['diff_missing_impact'] = merged['missing_impact_h'] - merged['missing_impact_a']
    merged = merged.copy()
    merged['target_win'] = merged['win_h'] 
    merged['target_margin'] = merged['actual_teamScore_h'] - merged['actual_teamScore_a']
    merged['target_total'] = merged['actual_teamScore_h'] + merged['actual_teamScore_a']
    
    return merged

# 建立集成模型 (Ensemble Builder)
def create_ensemble_model(base_estimator, params, n_estimators=5, type='classifier'):
    estimators = []
    print(f"   🧬 正在構建集成模型 (Ensemble size: {n_estimators})...")
    
    for i in range(n_estimators):
        model_params = params.copy()
        model_params['random_state'] = 42 + (i * 10) # 42, 52, 62...
        model_name = f'xgb_{i}'
        model = base_estimator(**model_params)
        estimators.append((model_name, model))
    
    if type == 'classifier':
        return VotingClassifier(estimators=estimators, voting='soft', n_jobs=-1)
    else:
        return VotingRegressor(estimators=estimators, n_jobs=-1)

def train():
    df = load_and_clean_data()
    
    if len(df) < 50:
        print(f"❌ 資料量過少，無法訓練。")
        exit()

    data = prepare_training_data(df)
    
    split_idx = int(len(data) * 0.85)
    train_data = data.iloc[:split_idx]
    test_data = data.iloc[split_idx:]
    
    print(f"\n📅 訓練區間: {train_data['gameDateTimeEst_h'].min().date()} ~ {train_data['gameDateTimeEst_h'].max().date()}")
    print(f"📅 驗證區間: {test_data['gameDateTimeEst_h'].min().date()} ~ {test_data['gameDateTimeEst_h'].max().date()}")
    
    # 確保只使用資料中實際存在的特徵
    available_features_spread = [f for f in TRAIN_FEATURES_SPREAD if f in data.columns]
    available_features_total = [f for f in TRAIN_FEATURES_TOTAL if f in data.columns]
    
    print(f"🚀 使用特徵數量 (Spread): {len(available_features_spread)} (包含 Roster Impact)")
    
    # --- 模型 1: 勝負預測 (Ensemble) ---
    print("\n🤖 訓練模型 1: 勝負預測 (Win/Loss Ensemble)...")
    model_win = create_ensemble_model(xgb.XGBClassifier, BEST_PARAMS_WIN, n_estimators=5, type='classifier')
    model_win.fit(train_data[available_features_spread], train_data['target_win'])
    
    acc = accuracy_score(test_data['target_win'], model_win.predict(test_data[available_features_spread]))
    print(f"   🎯 最終回測準確度: {acc*100:.2f}% (Ensemble)")
    
    # --- 模型 2: 讓分預測 (Ensemble) ---
    print("\n🤖 訓練模型 2: 讓分預測 (Spread Margin Ensemble)...")
    model_spread = create_ensemble_model(xgb.XGBRegressor, BEST_PARAMS_SPREAD, n_estimators=5, type='regressor')
    model_spread.fit(train_data[available_features_spread], train_data['target_margin'])
    
    mae = mean_absolute_error(test_data['target_margin'], model_spread.predict(test_data[available_features_spread]))
    print(f"   📏 平均誤差 (MAE): {mae:.2f} 分 (Ensemble)")
    
    # --- 模型 3: 大小分預測 (Ensemble) ---
    print("\n🤖 訓練模型 3: 大小分預測 (Total Points Ensemble)...")
    model_total = create_ensemble_model(xgb.XGBRegressor, BEST_PARAMS_TOTAL, n_estimators=5, type='regressor')
    model_total.fit(train_data[available_features_total], train_data['target_total'])
    
    mae = mean_absolute_error(test_data['target_total'], model_total.predict(test_data[available_features_total]))
    print(f"   📏 平均誤差 (MAE): {mae:.2f} 分 (Ensemble)")
    
    # --- 儲存 ---
    joblib.dump(model_win, 'model_win.pkl')
    joblib.dump(model_spread, 'model_spread.pkl')
    joblib.dump(model_total, 'model_total.pkl')
    joblib.dump(available_features_spread, 'features_spread.pkl')
    joblib.dump(available_features_total, 'features_total.pkl')
    joblib.dump(ROLLING_WINDOWS, 'rolling_config.pkl') 
    
    print("\n💾 V9.5 (Ensemble + Impact) 模型訓練完成！所有系統已就緒。")

if __name__ == "__main__":
    train()