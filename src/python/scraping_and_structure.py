from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
import time
import os
import requests
from datetime import datetime

# Use a headless chrome so you dont have a page opening every time you run.

# Also setting the chrome driver up is different mac/pc
# but basically you want the versions to match
# Google 'chrome driver' for more
options = Options()
options.add_argument('--headless=new')
service = Service('/usr/local/bin/chromedriver')
driver = webdriver.Chrome(service=service, options=options)

# Go to the page
url = 'https://planning.lacity.gov/about/commissions-boards-hearings#commissions'
driver.get(url)
time.sleep(5)

# Base path to create file library
base_path = '/Users/iggy/Documents/KUNG_RA/laplanningcouncil/cityplanningcomission'

# Document types by column index
file_labels = {
    3: 'agenda.pdf',
    4: 'supplemental-docs.pdf',
    5: 'audio.pdf',
    6: 'minutes.pdf'
}

# Loop through all years from 2025 to 2003
for year in range(2025, 2002, -1):
        print(f"Processing year: {year}")

        # We mainly use selenium because we need to select multiple tables that come from the dropdown menu
        
        # Choose your comission
        apc_select = Select(driver.find_element(By.NAME, 'apc'))
        apc_select.select_by_visible_text('City Planning Commission')
        # Choose your year
        year_select = Select(driver.find_element(By.NAME, 'date'))
        year_select.select_by_visible_text(str(year))
        time.sleep(3) # wait for the dropdown data to load

        rows = driver.find_elements(By.XPATH, "//table//tr")

        for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) < 7:
                    continue

                raw_date = cells[0].text.strip()
                if not raw_date:
                    continue

                # Convert MM/DD/YYYY to YYYY-MM-DD
                hearing_date = datetime.strptime(raw_date, "%m/%d/%Y").strftime("%Y-%m-%d")
                folder_path = os.path.join(base_path, str(year), hearing_date)
                os.makedirs(folder_path, exist_ok=True)

                for index in range(3, 7):  # Agenda, Supplemental Docs, Audio, Minutes
                        links = cells[index].find_elements(By.TAG_NAME, "a")
                        if not links:
                            continue

                        link = links[0].get_attribute("href")
                        if not link:
                            continue

                        filename = file_labels.get(index)
                        filepath = os.path.join(folder_path, filename)

                        response = requests.get(link)
                        with open(filepath, 'wb') as f:
                            f.write(response.content)

                        print(f"Saved: {year}/{hearing_date}/{filename}")