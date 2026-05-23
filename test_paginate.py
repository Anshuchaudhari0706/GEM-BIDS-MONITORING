from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

def test_paginate():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        print("Loading GeM bidlists...")
        driver.get("https://bidplus.gem.gov.in/bidlists")
        time.sleep(3)

        src = driver.page_source
        soup = BeautifulSoup(src, 'html.parser')
        bids = soup.find_all('div', class_='card')
        print(f"Page 1: {len(bids)} bids")

        print("Paginating to page 2 via JS...")
        # Gem uses the function `paginate(page_number)` 
        driver.execute_script("if(typeof paginate === 'function') paginate(2);")
        time.sleep(4)

        src = driver.page_source
        soup = BeautifulSoup(src, 'html.parser')
        bids2 = soup.find_all('div', class_='card')
        print(f"Page 2: {len(bids2)} bids")
        if len(bids2) > 0:
            print(" -", bids2[0].find('a', class_='bid_no_hover').text.strip())

    except Exception as e:
        print("Error:", e)
    finally:
        driver.quit()

test_paginate()
