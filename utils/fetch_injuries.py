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
            # 確保有抓到說明欄位 (第 5 個欄位)
            if len(cols) >= 5:
                try:
                    name_tag = cols[0].find('a')
                    if name_tag:
                        name = name_tag.text.strip()
                        status = cols[3].text.strip().lower()
                        desc = cols[4].text.lower() # 把說明文字轉小寫，方便搜尋
                        
                        # 🔥 終極升級：透過「說明欄位 (Col[4])」的關鍵字，精準給予戰力折損
                        if "out" in status or "expected to miss" in desc or "will be rested" in desc:
                            injuries[name] = 1.0  # 100% 缺席 (扣全額戰力)
                            
                        elif "day-to-day" in status:
                            if "doubtful" in desc:
                                injuries[name] = 0.75 # 大概率不打 (扣 75% 戰力)
                            elif "questionable" in desc:
                                injuries[name] = 0.5  # 50/50 機率 (扣一半戰力)
                            elif "probable" in desc:
                                injuries[name] = 0.0  # 大概率上場 (🔥 關鍵：不扣戰力！)
                            else:
                                injuries[name] = 0.5  # 找不到關鍵字，預設扣一半
                except:
                    continue
        
        print(f"✅ 抓取完成！共發現 {len(injuries)} 名傷兵/待定狀態球員。")
        return injuries
    except Exception as e:
        print(f"❌ 爬蟲錯誤: {e}")
        return {}