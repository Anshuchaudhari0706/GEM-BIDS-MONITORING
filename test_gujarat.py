from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

def test_gujarat_search():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        driver.get("https://bidplus.gem.gov.in/bidlists")
        time.sleep(3)

        # Apply search for Gujarat
        driver.execute_script("$('#advSearch').show();")
        time.sleep(1)
        driver.execute_script("$('#search_by').val('Gujarat');")
        driver.execute_script("searchBid();")
        time.sleep(4)

        src = driver.page_source
        soup = BeautifulSoup(src, 'html.parser')
        
        print("Inputs:")
        for i in soup.find_all('input'):
            print(f"ID: {i.get('id')}, Name: {i.get('name')}, Placeholder: {i.get('placeholder')}")
        
        total_rec = soup.find('div', class_='totalRecord')
        print("Total Record text:", total_rec.get_text(strip=True) if total_rec else "Not found")

        bids = soup.find_all('div', class_='card')
        print(f"Found {len(bids)} bids on page 1")
        for b in bids[:2]:
            print(" -", b.find('a', class_='bid_no_hover').text.strip())
            
    finally:
        driver.quit()

test_gujarat_search()
