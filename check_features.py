import joblib
import pandas as pd
import matplotlib.pyplot as plt
import xgboost as xgb

def plot_importance(model_path, feature_names_path, title):
    print(f"🔍 分析 {title} 的關鍵特徵...")
    try:
        # 載入模型與特徵列表
        model = joblib.load(model_path)
        feature_names = joblib.load(feature_names_path)
        
        # 取得特徵重要性
        # XGBoost sklearn API 裡，feature_importances_ 屬性直接提供了重要性
        importance = model.feature_importances_
        
        # 建立 DataFrame
        df_imp = pd.DataFrame({
            'Feature': feature_names,
            'Importance': importance
        }).sort_values('Importance', ascending=False)
        
        print(f"\n🏆 {title} - 前 10 大關鍵因素：")
        print(df_imp.head(10).to_string(index=False))
        print("-" * 30)
        
        return df_imp
    except Exception as e:
        print(f"❌ 無法讀取 {title}: {e}")
        return None

if __name__ == "__main__":
    # 檢查勝負預測模型
    plot_importance('model_win.pkl', 'features_spread.pkl', '勝負預測 (Win/Loss)')
    
    # 檢查讓分預測模型
    plot_importance('model_spread.pkl', 'features_spread.pkl', '讓分預測 (Spread)')
    
    # 檢查大小分預測模型
    plot_importance('model_total.pkl', 'features_total.pkl', '大小分預測 (Total)')