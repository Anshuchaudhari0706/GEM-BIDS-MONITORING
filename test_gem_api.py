"""
Test: Extract CSRF token via Selenium, then call GeM's internal /all-bids-data API 
with today's date filter directly.
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import requests
import time
import json

def get_gem_bids_via_api():
    # Step 1: Load page in Selenium to get session cookies + CSRF token
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    print("Loading GeM page to get session/CSRF...")
    driver.get("https://bidplus.gem.gov.in/bidlists")
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "block_header")))
    time.sleep(3)

    # Step 2: Extract CSRF token from page JS or cookies
    csrt = None
    try:
        csrt = driver.execute_script("return document.querySelector('[name=csrt]')?.value || window._token || null")
    except:
        pass

    # Also check cookies
    cookies = {c['name']: c['value'] for c in driver.get_cookies()}
    print("Cookies:", list(cookies.keys()))

    # Try to get CSRF from the network URL captured in page source
    src = driver.page_source
    import re
    csrt_matches = re.findall(r'csrt=([a-f0-9]+)', src)
    if csrt_matches:
        csrt = csrt_matches[0]
        print(f"CSRF token from page: {csrt}")
    else:
        print("No CSRF in page source, checking meta tags...")
        meta_matches = re.findall(r'<meta[^>]+csrf[^>]+content="([^"]+)"', src, re.IGNORECASE)
        if meta_matches:
            csrt = meta_matches[0]
            print(f"CSRF from meta: {csrt}")

    # Step 3: Build session with Selenium cookies
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'Referer': 'https://bidplus.gem.gov.in/bidlists',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
    })
    for name, value in cookies.items():
        session.cookies.set(name, value, domain='bidplus.gem.gov.in')

    driver.quit()

    # Step 4: Call the API
    today = time.strftime('%d/%m/%Y')
    api_url = f"https://bidplus.gem.gov.in/all-bids-data"
    if csrt:
        api_url += f"?csrt={csrt}"

    params = {
        'bidStartDate': today,
        'page': 1,
    }

    print(f"\nCalling API: {api_url}")
    print(f"Params: {params}")
    
    resp = session.get(api_url, params=params, timeout=15)
    print(f"Status: {resp.status_code}")
    print(f"Content-Type: {resp.headers.get('Content-Type','')}")
    print(f"Response (first 1000 chars): {resp.text[:1000]}")

get_gem_bids_via_api()
