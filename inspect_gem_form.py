"""
Inspect GeM's advanced search form and sort mechanism to understand how to filter by date.
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time, re

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--window-size=1920,1080')
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/114.0.0.0 Safari/537.36')

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

try:
    driver.get("https://bidplus.gem.gov.in/bidlists")
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "block_header")))
    time.sleep(2)

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # 1. Find filter/search form inputs
    print("=== ALL INPUT FIELDS ===")
    inputs = soup.find_all('input')
    for inp in inputs:
        print(f"  id={inp.get('id','')} | name={inp.get('name','')} | placeholder={inp.get('placeholder','')} | type={inp.get('type','')}")

    print("\n=== ALL SELECT FIELDS ===")
    selects = soup.find_all('select')
    for s in selects:
        print(f"  id={s.get('id','')} | name={s.get('name','')}")
        opts = s.find_all('option')
        for o in opts[:5]:
            print(f"    option: {o.get('value','')} = {o.get_text(strip=True)}")

    print("\n=== FILTER SECTION HTML ===")
    filter_div = soup.find('div', class_='sidefilter') or soup.find('div', class_='filter-bid')
    if filter_div:
        print(filter_div.prettify()[:3000])

    # 2. Check what JS functions are available for filtering
    print("\n=== JAVASCRIPT FILTER FUNCTIONS ===")
    scripts = soup.find_all('script')
    for s in scripts:
        if s.string and any(k in s.string for k in ['bidStartDate', 'searchBid', 'filterBid', 'getBidList']):
            print(s.string[:2000])
            print("---")

finally:
    driver.quit()
