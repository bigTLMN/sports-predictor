import requests
from bs4 import BeautifulSoup

URL = "https://www.espn.com/nba/injuries"

def fetch_injury_report():
    print("🏥 正在爬取即時傷兵名單 (Source: ESPN)...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        resp = requests.get(URL, headers=headers, timeout=10)
        if resp.status_code != 200:
            return {}
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        injuries = {} 
        
        rows = soup.find_all('tr', class_='Table__TR')
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 4:
                try:
                    name_tag = cols[0].find('a')
                    if name_tag:
                        name = name_tag.text.strip()
                        status = cols[3].text.strip() 
                        
                        # 🔥 升級：給予不同的戰力折損係數
                        if "Out" in status or "Expected to miss" in status or "Doubtful" in status:
                            injuries[name] = 1.0  # 100% 缺席
                        elif "Questionable" in status or "Day-To-Day" in status:
                            injuries[name] = 0.5  # 50% 戰力折損
                except:
                    continue
        
        print(f"✅ 抓取完成！共發現 {len(injuries)} 名傷兵/待定狀態球員。")
        return injuries
    except Exception as e:
        print(f"❌ 爬蟲錯誤: {e}")
        return {}