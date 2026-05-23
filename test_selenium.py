from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import json

def test_scrape():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')
    
    # Enable CDP to intercept network requests
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    
    print("Setting up WebDriver...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    print("Fetching GeM bid listing page...")
    driver.get("https://bidplus.gem.gov.in/bidlists")
    
    # Wait for the bid cards to appear
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "block_header"))
        )
        print("Bid cards loaded!")
    except:
        print("Timed out waiting for bid cards, trying anyway...")
    
    time.sleep(3)
    
    # Capture all network requests to find the API endpoint
    logs = driver.get_log("performance")
    api_urls = []
    for log in logs:
        msg = json.loads(log["message"])["message"]
        if msg["method"] == "Network.responseReceived":
            url = msg["params"]["response"]["url"]
            if "gem.gov.in" in url and any(k in url for k in ["bid", "api", "list", "json"]):
                api_urls.append(url)
    
    print("\nAPI Calls detected:")
    for u in api_urls:
        print(" ", u)
    
    # Save page source for analysis
    page_source = driver.page_source
    with open('gem_source2.html', 'w', encoding='utf-8') as f:
        f.write(page_source)
    
    # Parse for bid cards
    soup = BeautifulSoup(page_source, 'html.parser')
    bid_cards = soup.find_all('div', class_='block_header')
    print(f"\nFound {len(bid_cards)} bid cards")
    
    if bid_cards:
        for i, card in enumerate(bid_cards[:2]):
            print(f"\n--- BID {i+1} ---")
            print(card.get_text(separator=' | ', strip=True)[:500])
    
    driver.quit()

test_scrape()
