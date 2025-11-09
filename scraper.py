import re, json, urllib.request, time
from datetime import datetime
from collections import defaultdict

SEASON_ID = "842514138"
TEAM_ID = "1441922147"
BASE = "https://www.trackwrestling.com/tw/seasons"

# The EXACT URL you gave
schedule_url = f"{BASE}/LoadBalance.jsp?seasonId={SEASON_ID}&gbId=36&pageName=TeamSchedule.jsp;teamId={TEAM_ID}"

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')

print("Fetching 2024-25 Team Schedule...")
html = fetch(schedule_url)

# Extract dual links from the season schedule page
dual_links = re.findall(r'href="(/tw/seasons/DualResults\.jsp\?eventId=(\d+)&teamId=\d+)">([^<]+)</a>', html)
# Fallback to initDataGrid if no HTML links
if not dual_links:
    js_match = re.search(r'initDataGrid\(1000, false, "(\[\[.*?\]\])"', html)
    if js_match:
        raw = js_match.group(1).replace('\\"', '"')
        data = json.loads(raw)
        dual_links = [(f"/tw/seasons/DualResults.jsp?eventId={row[8]}&teamId={TEAM_ID}", row[8], row[2]) for row in data]

all_duals = []
total_wins = total_losses = 0
wrestlers = defaultdict(lambda: {"wins":0, "losses":0, "points":0.0, "weight":""})

for link_path, event_id, title in dual_links:
    date_match = re.search(r'(\d{1,2}/\d{1,2}(/\d{4})?)', title)
    date = date_match.group(1) if date_match else datetime.now().strftime("%m/%d
