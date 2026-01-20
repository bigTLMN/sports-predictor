from config import get_supabase_client

def test_connection():
    print("正在連線到 Supabase...")
    supabase = get_supabase_client()
    
    # 測試寫入資料：新增一個聯盟 "NBA"
    # upsert 的意思是：如果 "NBA" 已經存在就更新，不存在就新增
    data = {"name": "NBA"}
    
    try:
        response = supabase.table("leagues").upsert(data).execute()
        print("✅ 寫入成功！資料庫回應：")
        print(response.data)
        
        # 測試讀取資料
        read_response = supabase.table("leagues").select("*").execute()
        print("\n📋 目前資料庫裡的聯盟：")
        for league in read_response.data:
            print(f"- ID: {league['id']}, Name: {league['name']}")
            
    except Exception as e:
        print(f"❌ 發生錯誤：{e}")

if __name__ == "__main__":
    test_connection()