import re, json, urllib.request
from datetime import datetime
from collections import defaultdict

TEAM_ID = "1441922147"
BASE = "https://www.trackwrestling.com"

def fetch(url):
    return urllib.request.urlopen(url).read().decode()

# Duals
dual_html = fetch(f"{BASE}/teamprofile/TeamMatches.jsp?teamId={TEAM_ID}")
dual_js = re.search(r'initDataGrid\(1000, false, "(\[\[.*?\]\])"', dual_html).group(1)
dual_js = dual_js.replace('\\"', '"')
duals = json.loads(dual_js)

# Individual matches
match_html = fetch(f"{BASE}/teamprofile/TeamMatches.jsp?teamId={TEAM_ID}&eventType=1")
match_js = re.search(r'initDataGrid\(1000, false, "(\[\[.*?\]\])"', match_html)
matches = json.loads(match_js.group(1).replace('\\"', '"')) if match_js else []

# Parse duals
dual_list = []
wins = losses = 0
for d in duals:
    date = datetime.strptime(d[3], "%Y%m%d").strftime("%m/%d")
    shawnee_score = d[19] if d[16]=='Shawnee' else d[22]
    opp_score = d[22] if d[16]=='Shawnee' else d[19]
    result = "W" if shawnee_score > opp_score else "L"
    if result == "W": wins += 1
    else: losses += 1
    opp = d[2].split(" vs ")[0].replace(", NJ","").replace("West Windsor-Plainsboro North","WW-P North")
    dual_list.append({"date":date, "opponent":opp, "score":f"{shawnee_score}-{opp_score}", "result":result})

# Parse individuals
wrestlers = defaultdict(lambda: {"wins":0,"losses":0,"points":0.0,"weight":""})
for m in matches:
    w1 = f"{m[16]} {m[17]}".strip()
    w2 = f"{m[20]} {m[21]}".strip()
    winner = w1 if m[14] == m[14] else w2
    loser = w2 if winner == w1 else w1
    weight = m[1]
    if "Shawnee" in (m[18] if winner == w1 else m[22]):
        wrestlers[winner]["wins"] += 1
        wrestlers[winner]["points"] += float(m[33]) if m[33] not in ["",None] else 0
        wrestlers[winner]["weight"] = weight
    else:
        wrestlers[loser]["losses"] += 1
        wrestlers[loser]["weight"] = weight

ind_list = [{"name":name, "weight":d["weight"], "record":f"{d['wins']}-{d['losses']}", "points":d["points"]} for name,d in wrestlers.items()]
ind_list.sort(key=lambda x: int(x["weight"] or 999))

# Save
data = {"dualRecord": f"{wins}–{losses}", "duals": dual_list, "individuals": ind_list}
with open("data.json","w") as f: json.dump(data, f)

with open("index.html") as f: html = f.read()
html = re.sub(r'<div class="record">.*?</div>', f'<div class="record">{wins}–{losses}</div>', html)
with open("index.html","w") as f: f.write(html)

print("Site updated!")
