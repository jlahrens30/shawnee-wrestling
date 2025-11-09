import json
import re
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('--window-size=1920,1080')
options.add_argument('--disable-extensions')
options.add_argument('--disable-logging')
options.add_argument('--disable-sync')

driver = webdriver.Chrome(options=options)

try:
    print("Opening Trackwrestling season page...")
    driver.get("https://www.trackwrestling.com/tw/seasons/LoadBalance.jsp?seasonId=842514138&gbId=36&pageName=TeamSchedule.jsp;teamId=1441922147")
    time.sleep(8)

    html = driver.page_source
    print(f"Page loaded: {len(html)} characters")

    grid = re.search(r'initDataGrid\(1000, false, "(\[\[.*?\]\])"', html)
    if not grid:
        raise Exception("No schedule grid found!")
    
    print("Schedule grid found!")
    events = json.loads(grid.group(1).replace('\\"', '"'))

    duals_to_scrape = []
    for e in events:
        if len(e) > 21 and e[18] and e[21]:
            dual_id = e[0]
            name = e[2]
            date = f"{e[3][:4]}-{e[3][4:6]}-{e[3][6:8]}"
            shawnee_score = e[21] if e[16] == "Shawnee" else e[18]
            opp_score = e[18] if e[16] == "Shawnee" else e[21]
            duals_to_scrape.append((dual_id, name, date, int(shawnee_score), int(opp_score)))

    print(f"Found {len(duals_to_scrape)} duals with results")

    all_duals = []
    for dual_id, name, date, shawnee_total, opp_total in duals_to_scrape:
        print(f"Scraping dual {dual_id}...")
        driver.get(f"https://www.trackwrestling.com/tw/seasons/LoadBalance.jsp?seasonId=842514138&pageName=DualMatches.jsp&dualId={dual_id}")
        time.sleep(6)

        html = driver.page_source
        grid = re.search(r'initDataGrid\(1000, false, "(\[\[.*?\]\])"', html)
        if not grid:
            continue

        bouts = json.loads(grid.group(1).replace('\\"', '"'))
        matches = []

        for b in bouts:
            weight = b[16]
            winner = f"{b[20]} {b[21]}".strip()
            loser = f"{b[24]} {b[25]}".strip()
            winner_team = b[22]
            result = b[4]
            points = float(b[7]) if b[7] else 0.0
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

    print(f"SUCCESS! {len(all_duals)} duals saved → https://shawnee-wrestling.github.io")

finally:
    driver.quit()
