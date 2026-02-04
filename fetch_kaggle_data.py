import os
import zipfile
from kaggle.api.kaggle_api_extended import KaggleApi

def update_data():
    # 1. 驗證 (會自動讀取環境變數 KAGGLE_USERNAME 和 KAGGLE_KEY)
    api = KaggleApi()
    api.authenticate()

    print("⬇️ 正在從 Kaggle 下載最新的 TeamStatistics.csv ...")
    
    # 設定目標資料夾
    DATA_DIR = 'data'
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    # 2. 下載指定檔案
    # dataset 參數來自網址: kaggle.com/datasets/[eoinamoore/historical-nba-data-and-player-box-scores]
    api.dataset_download_file(
        dataset='eoinamoore/historical-nba-data-and-player-box-scores',
        file_name='TeamStatistics.csv',
        path=DATA_DIR,
        force=True  # 強制覆蓋舊檔案
    )

    # 3. 處理 Zip 檔 (Kaggle API 下載 CSV 時通常會包成 zip)
    zip_path = os.path.join(DATA_DIR, 'TeamStatistics.csv.zip')
    csv_path = os.path.join(DATA_DIR, 'TeamStatistics.csv')

    if os.path.exists(zip_path):
        print("📦 偵測到 Zip 檔，正在解壓縮...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(DATA_DIR)
        
        os.remove(zip_path) # 刪除 zip 檔保持乾淨
        print(f"✅ 解壓縮完成！已更新: {csv_path}")
    elif os.path.exists(csv_path):
        print(f"✅ 下載完成 (無須解壓縮): {csv_path}")
    else:
        print("❌ 下載失敗，找不到檔案。")

if __name__ == "__main__":
    update_data()