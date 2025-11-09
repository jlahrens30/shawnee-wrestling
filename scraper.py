from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pandas as pd
import time, json
from datetime import datetime

options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

service = Service("/usr/local/bin/chromedriver")
driver = webdriver.Chrome(service=service, options=options)

try:
    print("Opening TrackWrestling...")
    driver.get("https://www.trackwrestling.com/tw/seasons/LoadBalance.jsp?seasonId=842514138&gbId=36&pageName=PrintWrestlerMatches.jsp;teamId=1441922147")

    WebDriverWait(driver, 20).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "PageFrame")))
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "wrestlers")))

    driver.execute_script("document.getElementById('wrestlers').setAttribute('multiple', 'multiple');")
    select = driver.find_element(By.ID, "wrestlers")
    select.click()
    select.send_keys(Keys.CONTROL + "a")

    driver.find_element(By.XPATH, "//select[@id='levels']/option[text()='Varsity']").click()
    driver.find_element(By.XPATH, "//select[@id='eventIds']/option[1]").click()
    driver.find_element(By.XPATH, "//input[@value='Print']").click()

    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "table")))

    soup = BeautifulSoup(driver.page_source, "html.parser")
    tables = soup.find_all("table")
    df_list = pd.read_html(str(tables))
    full_df = pd.concat(df_list, ignore_index=True)

    duals = []
    current_dual = None
    for _, row in full_df.iterrows():
        if pd.notna(row[0]) and "vs" in str(row[0]):
            if current_dual:
                duals.append(current_dual)
            current_dual = {
                "opponent": str(row[0]).replace("Shawnee vs ", "").replace(" at ", "").strip(),
                "date": str(row[1]).strip(),
                "score": str(row[2]).strip(),
                "result": "W" if "Win" in str(row[3]) else "L",
                "matches": []
            }
        elif current_dual and len(row) >= 5:
            shawnee_name = str(row[1]).strip()
            opponent_name = str(row[3]).strip()
            result_text = str(row[2]).strip()
            shawnee_win = any(k in result_text.lower() for k in ["dec", "fall", "tf", "win"])

            current_dual["matches"].append({
                "weight": str(row[0]).strip(),
                "winner": shawnee_name if shawnee_win else opponent_name,
                "loser": opponent_name if shawnee_win else shawnee_name,
                "result": result_text,
                "points": str(row[4]).strip(),
                "shawneeWin": shawnee_win
            })
    if current_dual:
        duals.append(current_dual)

    wins = sum(1 for d in duals if d["result"] == "W")
    losses = sum(1 for d in duals if d["result"] == "L")

    data = {
        "season": "2024-25",
        "dualRecord": f"{wins}–{losses}",
        "duals": duals,
        "lastUpdated": datetime.now().strftime("%m/%d %I:%M %p")
    }

    with open("data.json", "w") as f:
        json.dump(data, f, indent=2)

    print(f"✅ SUCCESS — {len(duals)} duals scraped.")
except Exception as e:
    print("❌ ERROR:", e)
    raise
finally:
    driver.quit()
