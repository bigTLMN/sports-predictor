import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from supabase import create_client, Client

# 1. 載入 .env 檔案裡的設定
load_dotenv()

# 2. 取得環境變數
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

# 3. 建立連線並回傳 client 物件
def get_supabase_client() -> Client:
    if not url or not key:
        raise ValueError("請檢查 .env 檔案，確認 SUPABASE_URL 和 SUPABASE_KEY 是否已設定")
    
    # 回復成最簡單的連線方式，避免版本衝突
    return create_client(url, key)