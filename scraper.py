from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import json
from datetime import datetime
from bs4 import BeautifulSoup

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(options=options)

try:
    url = "https://www.trackwrestling.com/tw/seasons/LoadBalance.jsp?seasonId=842514138&gbId=36&pageName=PrintWrestlerMatches.jsp;teamId=1441922147"
    driver.get(url)
    time.sleep(8)

    iframe = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.ID, "PageFrame"))
    )
    driver.switch_to.frame(iframe)

    # Select all wrestlers
    driver.execute_script("document.getElementById('wrestlers').multiple = 'multiple'")
    time.sleep(1)
    driver.find_element(By.ID, "wrestlers").send_keys(Keys.SHIFT + Keys.END)

    # Select Varsity
    driver.find_element(By.XPATH, '//*[@id="levels"]/option[text()="Varsity"]').click()
    
    # Select All Events
    driver.find_element(By.XPATH, '//select[@id="eventIds"]/option[1]').click()

    # Click Print
    driver.find_element(By.XPATH, '//input[@value="Print"]').click()
    time.sleep(10)

    # Get printed page
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    tables = soup.find_all('table')

    duals = []
    current_dual = None

    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 6 and "vs" in cells[0].text:
                if current_dual:
                    duals.append(current_dual)
                current_dual = {
                    "opponent": cells[0].text.strip().replace("Shawnee vs ", "").replace(" at ", ""),
                    "date": cells[1].text.strip(),
                    "score": cells[2].text.strip(),
                    "result": "W" if "Win" in cells[3].text else "L",
                    "matches": []
                }
            elif current_dual and len(cells) >= 5:
                current_dual["matches"].append({
                    "weight": cells[0].text.strip(),
                    "shawnee": cells[1].text.strip(),
                    "result": cells[2].text.strip(),
                    "opponent": cells[3].text.strip(),
                    "points": cells[4].text.strip()
                })

    if current_dual:
        duals.append(current_dual)

    data = {
        "dualRecord": f"{sum(1 for d in duals if d['result']=='W')}–{sum(1 for d in duals if d['result']=='L')}",
        "duals": duals,
        "lastUpdated": datetime.now().strftime("%m/%d %I:%M %p")
    }

    with open("data.json", "w") as f:
        json.dump(data, f, indent=2)

    print("SUCCESS! Full data saved from PrintWrestlerMatches")

finally:
    driver.quit()
