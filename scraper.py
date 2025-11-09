from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import json
import time

URL = "https://www.trackwrestling.com/tw/seasons/LoadBalance.jsp?seasonId=842514138&gbId=36&pageName=PrintWrestlerMatches.jsp;teamId=1441922147"

def main():
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

    driver = webdriver.Chrome(options=opts)
    try:
        print("Loading page...")
        driver.get(URL)
        WebDriverWait(driver, 30).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "PageFrame")))
        time.sleep(5)

        # Select all wrestlers
        driver.execute_script("document.getElementById('wrestlers').setAttribute('multiple','multiple')")
        wrestlers = driver.find_element(By.ID, "wrestlers")
        wrestlers.send_keys(Keys.CONTROL, "a")

        # Varsity + all events
        driver.find_element(By.XPATH, "//select[@id='levels']/option[text()='Varsity']").click()
        driver.find_element(By.XPATH, "//select[@id='eventIds']/option[1]").click()

        # Print
        driver.find_element(By.XPATH, "//input[@value='Print']").click()
        WebDriverWait(driver, 30).until(lambda d: "PrintWrestlerMatches" in d.title)
        time.sleep(8)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        tables = soup.find_all("table")
        if not tables:
            raise RuntimeError("No tables found on page")

        df_list = pd.read_html(str(tables))
        df = pd.concat(df_list, ignore_index=True)

        duals = []
        current = None
        for _, row in df.iterrows():
            if pd.notna(row[0]) and "vs" in str(row[0]):
                if current:
                    duals.append(current)
                current = {
                    "opponent": str(row[0]).replace("Shawnee vs ", "").strip(),
                    "date": str(row[1]).strip(),
                    "score": str(row[2]).strip(),
                    "result": "W" if "Win" in str(row[3]) else "L",
                    "matches": []
                }
            elif current and len(row) >= 5:
                current["matches"].append({
                    "weight": str(row[0]).strip(),
                    "shawnee": str(row[1]).strip(),
                    "result": str(row[2]).strip(),
                    "opponent": str(row[3]).strip(),
                    "points": str(row[4]).strip()
                })
        if current:
            duals.append(current)

        wins = sum(1 for d in duals if d["result"] == "W")
        losses = sum(1 for d in duals if d["result"] == "L")

        data = {
            "season": "2024–25",
            "dualRecord": f"{wins}-{losses}",
            "duals": duals,
            "lastUpdated": datetime.now().strftime("%m/%d %I:%M %p")
        }

        with open("data.json", "w") as f:
            json.dump(data, f, indent=2)

        print(f"✅ Scraped {len(duals)} duals successfully")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
