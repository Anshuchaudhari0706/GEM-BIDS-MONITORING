from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

def test_gem_search():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        print("Loading GeM bidlists...")
        driver.get("https://bidplus.gem.gov.in/bidlists")
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "block_header")))
        time.sleep(2)

        today_str = time.strftime('%d-%m-%Y')
        print(f"Setting search for {today_str}...")

        # Open advanced search
        driver.execute_script("$('#advSearch').show();")
        time.sleep(1)

        # Set start date (from & to) to today
        driver.execute_script(f"$('#bidStartDate').val('{today_str}');")
        driver.execute_script(f"$('#bidEndDate').val('{today_str}');")
        
        # Trigger search
        print("Triggering searchBid()...")
        driver.execute_script("searchBid();")
        time.sleep(5)

        # Get total records
        src = driver.page_source
        soup = BeautifulSoup(src, 'html.parser')
        total_rec = soup.find('div', class_='totalRecord')
        if total_rec:
            print(f"Total Record text: {total_rec.get_text(strip=True)}")

        bids = soup.find_all('div', class_='card')
        print(f"Found {len(bids)} bids on page 1")
        
        for b in bids[:2]:
            print(" -", b.find('a', class_='bid_no_hover').text.strip())

    except Exception as e:
        print("Error:", e)
    finally:
        driver.quit()

test_gem_search()
