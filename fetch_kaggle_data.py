import os
import zipfile
from dotenv import load_dotenv

# 🔥 關鍵修正：必須在 import kaggle 之前先載入環境變數！
# 這樣 Kaggle 套件載入時，就能在環境變數裡看到 KAGGLE_USERNAME 和 KAGGLE_KEY
load_dotenv()

# 在載入 .env 之後，才 import kaggle
from kaggle.api.kaggle_api_extended import KaggleApi

# 設定 Kaggle 資料集名稱
DATASET_NAME = 'eoinamoore/historical-nba-data-and-player-box-scores'

# 設定要下載的檔案清單
FILES_TO_DOWNLOAD = [
    'TeamStatistics.csv',
    'PlayerStatistics.csv' 
]

def update_data():
    # 這裡可以再次檢查，確保有抓到
    if not os.getenv("KAGGLE_USERNAME") or not os.getenv("KAGGLE_KEY"):
        print("❌ 錯誤: 尚未讀取到 Kaggle 憑證。")
        print("   請確認 .env 檔案內容是否正確 (KAGGLE_USERNAME=..., KAGGLE_KEY=...)")
        return

    # 驗證
    try:
        api = KaggleApi()
        api.authenticate()
        print("✅ Kaggle API 驗證成功")
    except Exception as e:
        print(f"❌ Kaggle API 驗證失敗: {e}")
        return

    DATA_DIR = 'data'
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    # 迴圈下載檔案
    for file_name in FILES_TO_DOWNLOAD:
        print(f"\n⬇️ 正在下載: {file_name} ...")
        
        try:
            # 下載指定檔案
            api.dataset_download_file(
                dataset=DATASET_NAME,
                file_name=file_name,
                path=DATA_DIR,
                force=True
            )
            
            # 處理 Zip 檔
            zip_name = file_name + '.zip'
            zip_path = os.path.join(DATA_DIR, zip_name)
            csv_path = os.path.join(DATA_DIR, file_name)

            if os.path.exists(zip_path):
                print(f"   📦 正在解壓縮 {zip_name}...")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(DATA_DIR)
                
                os.remove(zip_path) # 刪除 zip 檔
                print(f"   ✅ 已解壓並更新: {csv_path}")
                
            elif os.path.exists(csv_path):
                print(f"   ✅ 下載完成: {csv_path}")
            else:
                print(f"   ❌ 下載似乎完成了，但找不到檔案: {csv_path}")

        except Exception as e:
            print(f"   ❌ 下載 {file_name} 失敗: {e}")

    print("\n🎉 所有數據更新完成！")

if __name__ == "__main__":
    update_data()