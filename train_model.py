import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_absolute_error
import joblib

# ==========================================
# 1. 基礎特徵 (Raw Features)
# ==========================================
RAW_FEATURES = [
    'fieldGoalsPercentage', 'threePointersPercentage', 'freeThrowsPercentage',
    'reboundsTotal', 'assists', 'steals', 'blocks', 'turnovers', 
    'plusMinusPoints', 'pointsInThePaint', 'teamScore' # 加入平均得分，對大小分很重要
]

def load_and_clean_data():
    print("📂 [V3] 正在讀取 TeamStatistics.csv ...")
    df = pd.read_csv('data/TeamStatistics.csv', low_memory=False)
    
    # 時間與空值處理
    df['gameDateTimeEst'] = pd.to_datetime(df['gameDateTimeEst'], utc=True)
    df = df.dropna(subset=['win', 'teamScore', 'opponentScore'])
    df['win'] = df['win'].astype(int)
    
    # 建立回歸目標 (Regression Targets)
    # 1. 勝分差 (Margin): 正數代表贏，負數代表輸
    df['margin'] = df['teamScore'] - df['opponentScore']
    # 2. 總得分 (Total): 兩隊加總
    df['total_points'] = df['teamScore'] + df['opponentScore']
    
    df = df.sort_values(['teamId', 'gameDateTimeEst'])
    return df

def feature_engineering_v3(df):
    print("🔄 [V3] 特徵工程：計算 Diff (讓分用) 與 Sum (大小分用)...")
    
    # 1. 計算自身滾動平均
    df_rolled = df.groupby('teamId')[RAW_FEATURES].apply(
        lambda x: x.shift(1).rolling(window=5, min_periods=1).mean()
    )
    new_cols = [f"rolling_{col}" for col in RAW_FEATURES]
    df_rolled.columns = new_cols
    df = pd.concat([df, df_rolled], axis=1)
    df = df.dropna(subset=new_cols)

    # 2. 合併對手數據
    df_slim = df[['gameId', 'teamId'] + new_cols]
    df_merged = pd.merge(df, df_slim, on='gameId', suffixes=('', '_opp'))
    df_merged = df_merged[df_merged['teamId'] != df_merged['teamId_opp']]
    
    # 3. 產生特徵集
    spread_features = [] # 用於預測勝負 & 讓分
    total_features = []  # 用於預測大小分
    
    for col in RAW_FEATURES:
        # A. 差值特徵 (Diff): 用於讓分 (例: 我比你準 -> 我贏分)
        diff_col = f"diff_{col}"
        df_merged[diff_col] = df_merged[f"rolling_{col}"] - df_merged[f"rolling_{col}_opp"]
        spread_features.append(diff_col)
        
        # B. 總和特徵 (Sum): 用於大小分 (例: 我快你也快 -> 總分高)
        sum_col = f"sum_{col}"
        df_merged[sum_col] = df_merged[f"rolling_{col}"] + df_merged[f"rolling_{col}_opp"]
        total_features.append(sum_col)
    
    # 加入主場因素
    df_merged['is_home'] = df_merged['home'].apply(lambda x: 1 if x == True else 0)
    spread_features.append('is_home')
    total_features.append('is_home') # 大小分有時候跟主客場也有關
    
    return df_merged, spread_features, total_features

def train_models(df, spread_cols, total_cols):
    models = {}
    
    # ==========================================
    # Model 1: 勝負分類 (Classifier)
    # ==========================================
    print(f"\n🤖 訓練模型 1: 勝負預測 (Win/Loss)...")
    X = df[spread_cols]
    y = df['win']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    
    clf = xgb.XGBClassifier(
        n_estimators=200, learning_rate=0.03, max_depth=4,
        objective='binary:logistic', eval_metric='logloss', use_label_encoder=False
    )
    clf.fit(X_train, y_train)
    acc = accuracy_score(y_test, clf.predict(X_test))
    print(f"   🎯 勝率準確度: {acc:.2%}")
    models['win'] = clf
    
    # ==========================================
    # Model 2: 讓分預測 (Spread Regressor)
    # ==========================================
    print(f"\n🤖 訓練模型 2: 讓分預測 (Spread Margin)...")
    y_spread = df['margin'] # 目標是贏幾分
    X_train, X_test, y_train, y_test = train_test_split(X, y_spread, test_size=0.2, shuffle=False)
    
    reg_spread = xgb.XGBRegressor(
        n_estimators=300, learning_rate=0.03, max_depth=5,
        objective='reg:squarederror' # 回歸問題
    )
    reg_spread.fit(X_train, y_train)
    mae_spread = mean_absolute_error(y_test, reg_spread.predict(X_test))
    print(f"   📏 平均誤差 (MAE): {mae_spread:.2f} 分 (越低越好)")
    models['spread'] = reg_spread
    
    # ==========================================
    # Model 3: 大小分預測 (Total Regressor)
    # ==========================================
    print(f"\n🤖 訓練模型 3: 大小分預測 (Total Points)...")
    X_total = df[total_cols] # 注意：這裡用 sum 特徵
    y_total = df['total_points']
    X_train, X_test, y_train, y_test = train_test_split(X_total, y_total, test_size=0.2, shuffle=False)
    
    reg_total = xgb.XGBRegressor(
        n_estimators=300, learning_rate=0.03, max_depth=5,
        objective='reg:squarederror'
    )
    reg_total.fit(X_train, y_train)
    mae_total = mean_absolute_error(y_test, reg_total.predict(X_test))
    print(f"   📏 平均誤差 (MAE): {mae_total:.2f} 分")
    models['total'] = reg_total
    
    return models

if __name__ == "__main__":
    try:
        df = load_and_clean_data()
        df_final, spread_feats, total_feats = feature_engineering_v3(df)
        
        models = train_models(df_final, spread_feats, total_feats)
        
        # 存檔：這次有三個模型 + 兩組特徵
        joblib.dump(models['win'], 'model_win.pkl')
        joblib.dump(models['spread'], 'model_spread.pkl')
        joblib.dump(models['total'], 'model_total.pkl')
        joblib.dump(spread_feats, 'features_spread.pkl')
        joblib.dump(total_feats, 'features_total.pkl')
        
        print("\n💾 所有模型與特徵已儲存完畢！")
            
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()