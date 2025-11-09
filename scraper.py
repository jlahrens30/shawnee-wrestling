import re
import json
import urllib.request
from datetime import datetime
from collections import defaultdict

TEAM_ID = "1441922147"
SEASON_ID = "842514138"
BASE = "https://www.trackwrestling.com"

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'ShawneeWrestlingBot/1.0'})
    return urllib.request.urlopen(req, timeout=30).read().decode('utf-8', errors='ignore')

# 1. GET FULL SCHEDULE
print("Fetching full 2024-25 schedule...")
schedule_html = fetch(f"{BASE}/tw/seasons/LoadBalance.jsp?seasonId={SEASON_ID}&gbId=36&pageName=TeamSchedule.jsp;teamId={TEAM_ID}")
grid_match = re.search(r'initDataGrid\(1000, false, "(\[\[.*?\]\])"', schedule_html)
events = json.loads(grid_match.group(1).replace('\\"', '"')) if grid_match else []

schedule = []
dual_urls = []

for e in events:
    event_id = e[0]
    name = e[2]
    date_str = f"{e[3][:4]}-{e[3][4:6]}-{e[3][6:8]}"
    is_dual = e[11] == "D" or " vs " in name or " @ " in name
    dual_id = e[0] if is_dual else None
    
    score = ""
    result = ""
    if len(e) > 21 and e[18] and e[21]:
        shawnee_score = e[21] if e[16] == "Shawnee" else e[18]
        opp_score = e[18] if e[16] == "Shawnee" else e[21]
        score = f"{shawnee_score}–{opp_score}"
        result = "W" if int(shawnee_score) > int(opp_score) else "L"
    
    schedule.append({
        "date": date_str,
        "name": name.replace("Shawnee, NJ @ ", "").replace(" @ Shawnee, NJ", " (Home)").replace(", NJ", ""),
        "score": score,
        "result": result,
        "dualId": dual_id
    })
    
    if dual_id and score:  # only scrape duals with results
        dual_urls.append((dual_id, name, date_str))

# 2. SCRAPE EVERY DUAL WITH FULL BOX SCORES
all_duals = []
wrestlers = defaultdict(lambda: {"wins": 0, "losses": 0, "points": 0.0, "weight": ""})

for dual_id, event_name, date in dual_urls:
    print(f"  → Scraping dual {dual_id}: {event_name}")
    dual_url = f"{BASE}/tw/seasons/LoadBalance.jsp?seasonId={SEASON_ID}&pageName=DualMatches.jsp&dualId={dual_id}"
    html = fetch(dual_url)
    
    grid = re.search(r'initDataGrid\(1000, false, "(\[\[.*?\]\])"', html)
    if not grid:
        continue
        
    raw = grid.group(1).replace('\\"', '"')
    bouts = json.loads(raw)
    
    matches = []
    shawnee_total = opp_total = 0
    
    for b in bouts:
        weight = b[16]
        winner_name = f"{b[20]} {b[21]}".strip()
        loser_name = f"{b[24]} {b[25]}".strip()
        winner_team = b[22]
        loser_team = b[26]
        result = b[4]
        points = float(b[7]) if b[7] else 0.0
        
        is_shawnee_win = winner_team == "SHAW" or "Shawnee" in winner_team
        winner_display = winner_name if is_shawnee_win else loser_name
        loser_display = loser_name if is_shawnee_win else winner_name
        
        if is_shawnee_win:
            shawnee_total += points
            wrestlers[winner_name]["wins"] += 1
            wrestlers[winner_name]["points"] += points
        else:
            opp_total += points
            if "SHAW" in loser_team or "Shawnee" in loser_team:
                wrestlers[loser_name]["losses"] += 1
        
        wrestlers[winner_name]["weight"] = weight
        wrestlers[loser_name]["weight"] = weight
        
        matches.append({
            "weight": weight,
            "winner": winner_display,
            "loser": loser_display,
            "result": result,
            "points": points,
            "shawneeWin": is_shawnee_win
        })
    
    all_duals.append({
        "date": date,
        "opponent": event_name.split(" vs ")[0].split(" @ ")[0].replace("Shawnee", "").strip(),
        "score": f"{int(shawnee_total)}–{int(opp_total)}",
        "result": "W" if shawnee_total > opp_total else "L",
        "matches": matches
    })

# 3. INDIVIDUAL RECORDS
individuals = sorted([
    {"name": name, "weight": d["weight"], "record": f"{d['wins']}-{d['losses']}", "points": d["points"]}
    for name, d in wrestlers.items() if d["wins"] + d["losses"] > 0
], key=lambda x: int(x["weight"] or 999))

# 4. SAVE EVERYTHING
wins = sum(1 for d in all_duals if d["result"] == "W")
losses = len(all_duals) - wins

data = {
    "season": "2024-25",
    "dualRecord": f"{wins}–{losses}",
    "schedule": schedule,
    "duals": all_duals,
    "individuals": individuals,
    "lastUpdated": datetime.now().strftime("%m/%d %I:%M %p")
}

with open("data.json", "w") as f:
    json.dump(data, f, indent=2)

print(f"SUCCESS! {len(all_duals)} duals with full box scores + {len(individuals)} wrestlers")
print("LIVE AT: https://shawnee-wrestling.github.io")
