import optuna
import xgboost as xgb
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, mean_absolute_error
# 確保這裡 import 的是 train_model，且 train_model.py 內容已經是 V8.0 版本
from train_model import load_and_clean_data, prepare_training_data, TRAIN_FEATURES_SPREAD, TRAIN_FEATURES_TOTAL

# 讀取一次資料即可，不用重複讀取
print("📂 [Tuning] 讀取資料中...")
df = load_and_clean_data()
data = prepare_training_data(df)

# ==========================================
# 🔥 關鍵修正：確保特徵存在於 DataFrame 中
# 與 train_model.py 的邏輯保持一致，避免 KeyError
# ==========================================
FEATURES_SPREAD = [f for f in TRAIN_FEATURES_SPREAD if f in data.columns]
FEATURES_TOTAL = [f for f in TRAIN_FEATURES_TOTAL if f in data.columns]

print(f"🚀 [Tuning] 實際使用特徵數量: Spread={len(FEATURES_SPREAD)}, Total={len(FEATURES_TOTAL)}")
if len(FEATURES_SPREAD) < 20:
    print("⚠️ 警告：特徵數量似乎仍是舊版 (V7.1)，請確認 train_model.py 是否已更新為 V8.0 多重窗口版本。")

# 切分資料 (與 train_model.py 保持一致，85% 訓練 / 15% 驗證)
split_idx = int(len(data) * 0.85)
train_data = data.iloc[:split_idx]
test_data = data.iloc[split_idx:]

print(f"📊 訓練集: {len(train_data)}, 驗證集: {len(test_data)}")

# ==========================================
# 1. 調優目標：勝負預測 (Maximize Accuracy)
# ==========================================
def objective_win(trial):
    # 定義參數搜尋空間
    param = {
        'eval_metric': 'logloss',
        'booster': 'gbtree',
        # 移除 'use_label_encoder': False 以消除警告
        # 關鍵參數
        'n_estimators': trial.suggest_int('n_estimators', 100, 1000),
        'max_depth': trial.suggest_int('max_depth', 3, 10),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
        'subsample': trial.suggest_float('subsample', 0.5, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
        'gamma': trial.suggest_float('gamma', 0, 5),
        'reg_alpha': trial.suggest_float('reg_alpha', 0, 10),
        'reg_lambda': trial.suggest_float('reg_lambda', 0, 10),
        'missing': np.nan,
        'n_jobs': -1 # 加速訓練
    }

    model = xgb.XGBClassifier(**param)
    
    # 訓練 (使用過濾後的特徵列表 FEATURES_SPREAD)
    model.fit(train_data[FEATURES_SPREAD], train_data['target_win'])
    
    # 預測
    preds = model.predict(test_data[FEATURES_SPREAD])
    accuracy = accuracy_score(test_data['target_win'], preds)
    
    return accuracy

# ==========================================
# 2. 調優目標：讓分/大小 (Minimize MAE)
# ==========================================
def objective_reg(trial, target_col, features):
    param = {
        'objective': 'reg:squarederror',
        'booster': 'gbtree',
        'n_estimators': trial.suggest_int('n_estimators', 100, 1000),
        'max_depth': trial.suggest_int('max_depth', 3, 10),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
        'subsample': trial.suggest_float('subsample', 0.5, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
        'gamma': trial.suggest_float('gamma', 0, 5),
        'reg_alpha': trial.suggest_float('reg_alpha', 0, 10),
        'reg_lambda': trial.suggest_float('reg_lambda', 0, 10),
        'missing': np.nan,
        'n_jobs': -1 # 加速訓練
    }
    
    model = xgb.XGBRegressor(**param)
    # 訓練
    model.fit(train_data[features], train_data[target_col])
    
    # 預測
    preds = model.predict(test_data[features])
    mae = mean_absolute_error(test_data[target_col], preds)
    
    return mae

if __name__ == "__main__":
    # 設定 Optuna 顯示層級
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    print("\n🔍 開始尋找 [勝負預測] 的黃金參數...")
    study_win = optuna.create_study(direction='maximize')
    study_win.optimize(objective_win, n_trials=50) 
    print(f"   👉 Best Accuracy: {study_win.best_value:.4f}")
    
    print("\n🔍 開始尋找 [讓分預測] 的黃金參數...")
    study_spread = optuna.create_study(direction='minimize')
    # 使用過濾後的特徵 FEATURES_SPREAD
    study_spread.optimize(lambda trial: objective_reg(trial, 'target_margin', FEATURES_SPREAD), n_trials=50)
    print(f"   👉 Best MAE: {study_spread.best_value:.4f}")

    print("\n🔍 開始尋找 [大小分預測] 的黃金參數...")
    study_total = optuna.create_study(direction='minimize')
    # 使用過濾後的特徵 FEATURES_TOTAL
    study_total.optimize(lambda trial: objective_reg(trial, 'target_total', FEATURES_TOTAL), n_trials=50)
    print(f"   👉 Best MAE: {study_total.best_value:.4f}")
    
    print("\n" + "="*50)
    print("🏆 調優結果報告 (請將這些參數填回 train_model.py)")
    print("="*50)
    
    print("\n🤖 [Win Model] Best Accuracy:", study_win.best_value)
    print("Best Params:", study_win.best_params)
    
    print("\n🤖 [Spread Model] Best MAE:", study_spread.best_value)
    print("Best Params:", study_spread.best_params)
    
    print("\n🤖 [Total Model] Best MAE:", study_total.best_value)
    print("Best Params:", study_total.best_params)