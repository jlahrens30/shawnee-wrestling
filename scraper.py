import json
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

TEAM_ID = "1441922147"
SEASON_ID = "842514138"
BASE = "https://www.trackwrestling.com"

# Setup headless Chrome
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('--window-size=1920,1080')
driver = webdriver.Chrome(options=options)

def get_page_source(url):
    print(f"Loading {url}")
    driver.get(url)
    time.sleep(5)  # Wait for JS to load initDataGrid
    return driver.page_source

try:
    # 1. GET FULL SCHEDULE
    schedule_url = f"{BASE}/tw/seasons/LoadBalance.jsp?seasonId={SEASON_ID}&gbId=36&pageName=TeamSchedule.jsp;teamId={TEAM_ID}"
    html = get_page_source(schedule_url)
    
    grid = re.search(r'initDataGrid\(1000, false, "(\[\[.*?\]\])"', html)
    if not grid:
        raise Exception("No schedule data found")
    
    events = json.loads(grid.group(1).replace('\\"', '"'))
    
    duals_with_results = []
    for e in events:
        if len(e) > 21 and e[18] and e[21]:  # has scores
            dual_id = e[0]
            name = e[2]
            date = f"{e[3][:4]}-{e[3][4:6]}-{e[3][6:8]}"
            shawnee_score = e[21] if e[16] == "Shawnee" else e[18]
            opp_score = e[18] if e[16] == "Shawnee" else e[21]
            duals_with_results.append((dual_id, name, date, int(shawnee_score), int(opp_score)))
    
    # 2. SCRAPE EACH DUAL
    all_duals = []
    for dual_id, name, date, shawnee_total, opp_total in duals_with_results:
        print(f"Scraping dual {dual_id}: {name}")
        dual_url = f"{BASE}/tw/seasons/LoadBalance.jsp?seasonId={SEASON_ID}&pageName=DualMatches.jsp&dualId={dual_id}"
        html = get_page_source(dual_url)
        
        grid = re.search(r'initDataGrid\(1000, false, "(\[\[.*?\]\])"', html)
        if not grid:
            continue
            
        bouts = json.loads(grid.group(1).replace('\\"', '"'))
        matches = []
        
        for b in bouts:
            weight = b[16]
            winner_fname = b[20]
            winner_lname = b[21]
            loser_fname = b[24]
            loser_lname = b[25]
            winner_team = b[22]
            loser_team = b[26]
            result = b[4]
            points = float(b[7]) if b[7] else 0.0
            
            winner = f"{winner_fname} {winner_lname}".strip()
            loser = f"{loser_fname} {loser_lname}".strip()
            is_shawnee_win = "SHAW" in winner_team or "Shawnee" in winner_team
            
            matches.append({
                "weight": weight,
                "winner": winner if is_shawnee_win else loser,
                "loser": loser if is_shawnee_win else winner,
                "result": result,
                "points": points,
                "shawneeWin": is_shawnee_win
            })
        
        all_duals.append({
            "date": date,
            "opponent": name.split(" vs ")[0].split(" @ ")[0].replace("Shawnee", "").strip(),
            "score": f"{shawnee_total}–{opp_total}",
            "result": "W" if shawnee_total > opp_total else "L",
            "matches": matches
        })
    
    # 3. SAVE
    wins = sum(1 for d in all_duals if d["result"] == "W")
    losses = len(all_duals) - wins
    
    data = {
        "season": "2024-25",
        "dualRecord": f"{wins}–{losses}",
        "duals": all_duals,
        "lastUpdated": datetime.now().strftime("%m/%d %I:%M %p")
    }
    
    with open("data.json", "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"SUCCESS! {len(all_duals)} duals scraped with full box scores!")
    print("LIVE: https://shawnee-wrestling.github.io")

finally:
    driver.quit()
