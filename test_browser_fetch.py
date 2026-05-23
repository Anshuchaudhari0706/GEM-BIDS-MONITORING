"""
Test: Use Selenium to call GeM's internal API from within the browser using JavaScript fetch().
This bypasses the 403 because the request comes from the actual browser session.
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time, re, json

def get_gem_bids_from_browser():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--window-size=1920,1080')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        print("[1] Loading GeM bid list page...")
        driver.get("https://bidplus.gem.gov.in/bidlists")
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "block_header")))
        time.sleep(3)

        print(f"[1.5] Page title: {driver.title}")
        
        # Write page source to file for debugging
        src = driver.page_source
        with open('gem_source_fetch.html', 'w', encoding='utf-8') as f:
            f.write(src)
            
        print(f"[1.6] Page source length: {len(src)}")
        print(f"[1.7] Occurrences of 'csrt' in source: {src.lower().count('csrt')}")
        print(f"[1.8] Occurrences of 'csrf' in source: {src.lower().count('csrf')}")

        # Extract CSRF token name and hash value
        csrf_name = "csrf_bd_gem_nk"
        csrf_hash = ""
        try:
            soup = BeautifulSoup(src, 'html.parser')
            cname_input = soup.find('input', {'id': 'cname'})
            chash_input = soup.find('input', {'id': 'chash'})
            if cname_input:
                csrf_name = cname_input.get('value', 'csrf_bd_gem_nk')
            if chash_input:
                csrf_hash = chash_input.get('value', '')
        except Exception as e:
            print("Error parsing CSRF:", e)
            
        print(f"[2] CSRF Token Name: {csrf_name}")
        print(f"[2.1] CSRF Token Hash: {csrf_hash}")

        today = time.strftime('%d/%m/%Y')
        print(f"[3] Fetching today's bids for date: {today}")

        # Call the API from within browser using JavaScript fetch
        result = driver.execute_async_script("""
        var callback = arguments[arguments.length - 1];
        var csrfName = arguments[0];
        var csrfHash = arguments[1];
        var todayDate = arguments[2];
        
        var bodyData = csrfName + '=' + csrfHash + '&bidStartDate=' + todayDate + '&page=1';
        
        fetch('/all-bids-data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: bodyData
        })
        .then(r => r.text())
        .then(html => callback({success: true, html: html}))
        .catch(e => callback({success: false, error: e.toString()}));
        """, csrf_name, csrf_hash, today)

        if result and result.get('success'):
            res_text = result['html']
            print(f"[4] Got response. Length: {len(res_text)}")
            
            with open('gem_bids_sample.json', 'w', encoding='utf-8') as f:
                f.write(res_text)
                
            try:
                data = json.loads(res_text)
                docs = data.get('response', {}).get('response', {}).get('docs', [])
                print(f"[5] Found {len(docs)} bids in JSON response")
                if docs:
                    print("\n--- FIRST BID DETAILS ---")
                    print(json.dumps(docs[0], indent=2)[:1500])
            except Exception as e:
                print("Error parsing JSON:", e)
                print(res_text[:500])
        else:
            print(f"[!] Fetch failed: {result}")

    finally:
        driver.quit()

get_gem_bids_from_browser()
