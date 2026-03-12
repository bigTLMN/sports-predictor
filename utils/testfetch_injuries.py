import requests
from bs4 import BeautifulSoup

URL = "https://www.espn.com/nba/injuries"

def debug_injury_report():
    print("🔍 正在抓取 ESPN 傷兵名單，準備解析 HTML 結構...\n")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        resp = requests.get(URL, headers=headers, timeout=10)
        if resp.status_code != 200:
            print(f"❌ 網頁請求失敗，狀態碼: {resp.status_code}")
            return
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        rows = soup.find_all('tr', class_='Table__TR')
        
        print(f"✅ 總共找到 {len(rows)} 列資料 (<tr>)")
        print("👇 印出前 10 名球員的欄位對應狀況：\n" + "="*40)
        
        # 故意跳過表頭，並只印出前 10 筆資料來觀察
        player_count = 0
        for row in rows:
            cols = row.find_all('td')
            
            # 至少要有資料才印
            if len(cols) > 0:
                player_count += 1
                print(f"--- 測試資料 {player_count} ---")
                print(f"欄位數量: {len(cols)}")
                
                for i, col in enumerate(cols):
                    print(f"  Col[{i}]: {col.text.strip()}")
                
                if len(cols) >= 4:
                    name_tag = cols[0].find('a')
                    if name_tag:
                        print(f"  🎯 解析結果 => 球員: [{name_tag.text.strip()}], 狀態: [{cols[3].text.strip()}]")
                else:
                    print("  ⚠️ 這列的欄位不到 4 個，可能是表頭或分隔線。")
                
                print("-" * 40)
                
                if player_count >= 10:
                    break

    except Exception as e:
        print(f"❌ 爬蟲錯誤: {e}")

if __name__ == "__main__":
    debug_injury_report()