# utils/fetch_injuries.py
import requests
from bs4 import BeautifulSoup

# ESPN 傷兵頁面
URL = "https://www.espn.com/nba/injuries"

def fetch_injury_report():
    print("🏥 正在爬取即時傷兵名單 (Source: ESPN)...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        resp = requests.get(URL, headers=headers, timeout=10)
        if resp.status_code != 200:
            print("❌ 無法連線到 ESPN")
            return {}
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        injuries = {} 
        
        # 抓所有表格列
        rows = soup.find_all('tr', class_='Table__TR')
        
        count = 0
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 4:
                try:
                    name_tag = cols[0].find('a')
                    if name_tag:
                        name = name_tag.text.strip()
                        status = cols[3].text.strip() 
                        
                        # 判定是否缺陣
                        is_out = False
                        if "Out" in status or "Expected to miss" in status:
                            is_out = True
                        elif "Doubtful" in status:
                            is_out = True
                            
                        if is_out:
                            injuries[name] = "OUT"
                            count += 1
                except:
                    continue
        
        print(f"✅ 抓取完成！共發現 {count} 名確定缺陣 (OUT) 的球員。")
        return injuries

    except Exception as e:
        print(f"❌ 爬蟲錯誤: {e}")
        return {}