from flask import Flask, jsonify, request, send_from_directory
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import re
import threading
import logging

app = Flask(__name__, static_folder='.')
logging.basicConfig(level=logging.INFO)

# ─── Global State ───────────────────────────────────────────────────────────
scanned_bids = []
is_scanning = False
last_scan_time = None
scan_error = None
last_scan_date = None  # YYYY-MM-DD of the date that was scanned

def get_chrome_driver():
    """Create an undetected Chrome driver that bypasses GeM's bot detection."""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--window-size=1920,1080')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/114.0.0.0 Safari/537.36'
    )
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.set_script_timeout(180)
    return driver

def parse_json_docs(docs, filter_state=None, status_type='published'):
    """
    Parse bid documents from GeM JSON API docs list.
    """
    today_str = time.strftime('%d-%m-%Y')
    bids = []
    
    for doc in docs:
        try:
            bid_id = doc.get('b_bid_number', doc.get('id', ''))
            if isinstance(bid_id, list):
                bid_id = bid_id[0] if bid_id else ""
            
            if not bid_id:
                continue
                
            title = doc.get('bd_category_name', doc.get('b_category_name', ['OTHER']))
            if isinstance(title, list):
                title = title[0] if title else "OTHER"
                
            quantity = doc.get('b_total_quantity', [0])
            if isinstance(quantity, list):
                quantity = str(quantity[0]) if quantity else "0"
            else:
                quantity = str(quantity)
                
            dept_min = doc.get('ba_official_details_minName', [''])
            if isinstance(dept_min, list):
                dept_min = dept_min[0] if dept_min else ""
                
            dept_name = doc.get('ba_official_details_deptName', [''])
            if isinstance(dept_name, list):
                dept_name = dept_name[0] if dept_name else ""
                
            dept_parts = []
            if dept_min and dept_min != 'NA' and dept_min.strip():
                dept_parts.append(dept_min)
            if dept_name and dept_name != 'NA' and dept_name.strip():
                dept_parts.append(dept_name)
                
            department = " | ".join(dept_parts) if dept_parts else "Department details not specified"
            
            # Dates format in JSON is "2026-05-21T17:00:00Z"
            start_date_iso = doc.get('final_start_date_sort', [''])
            if isinstance(start_date_iso, list):
                start_date_iso = start_date_iso[0] if start_date_iso else ""
                
            end_date_iso = doc.get('final_end_date_sort', [''])
            if isinstance(end_date_iso, list):
                end_date_iso = end_date_iso[0] if end_date_iso else ""
                
            def iso_to_raw(iso_str):
                try:
                    date_part, time_part = iso_str.split('T')
                    yyyy, mm, dd = date_part.split('-')
                    time_part = time_part.replace('Z', '')
                    return f"{dd}-{mm}-{yyyy} {time_part}"
                except:
                    return iso_str
            
            raw_start_date = iso_to_raw(start_date_iso) if start_date_iso else ""
            raw_end_date = iso_to_raw(end_date_iso) if end_date_iso else ""
            
            # publishedDate & deadline are yyyy-mm-dd format
            published_date = start_date_iso.split('T')[0] if start_date_iso else today_str
            deadline = end_date_iso.split('T')[0] if end_date_iso else ""
            
            state = detect_state(department + " " + title)
            if filter_state and filter_state.upper() != 'ALL':
                state = filter_state
            
            city = detect_city(department + " " + title)
            category, employees = detect_category(title, quantity)
            
            bid_link = f"https://bidplus.gem.gov.in/showbidDocument/{doc.get('id', '')}"
            
            bids.append({
                "id": bid_id,
                "title": title[:150],
                "department": department[:200],
                "category": category,
                "employees": employees,
                "publishedDate": published_date,
                "deadline": deadline,
                "value": 0,
                "state": state,
                "city": city,
                "status": status_type,
                "emd": "As per document",
                "eligibility": "Refer to official bid document",
                "aiSummary": generate_ai_summary(title, category, employees, state),
                "gemLink": bid_link,
                "quantity": quantity,
                "rawStartDate": raw_start_date,
                "rawEndDate": raw_end_date,
            })
        except Exception as e:
            logging.warning(f"Error parsing JSON doc: {e}")
            continue
            
    return bids

def convert_date(date_str):
    """Convert dd-mm-yyyy to yyyy-mm-dd."""
    try:
        parts = date_str.strip().split('-')
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
    except:
        pass
    return date_str

def detect_state(text):
    """Detect Indian state from text."""
    states = {
        'Gujarat': ['gujarat', 'ahmedabad', 'surat', 'vadodara', 'gandhinagar', 'rajkot', 'bhavnagar', 'jamnagar'],
        'Maharashtra': ['maharashtra', 'mumbai', 'pune', 'nagpur', 'nashik'],
        'Delhi': ['delhi', 'new delhi', 'ndmc'],
        'Karnataka': ['karnataka', 'bangalore', 'bengaluru', 'mysuru'],
        'Tamil Nadu': ['tamil nadu', 'chennai', 'coimbatore', 'madurai'],
        'Uttar Pradesh': ['uttar pradesh', 'lucknow', 'noida', 'agra', 'kanpur'],
        'Rajasthan': ['rajasthan', 'jaipur', 'jodhpur', 'udaipur'],
        'West Bengal': ['west bengal', 'kolkata', 'howrah'],
        'Telangana': ['telangana', 'hyderabad', 'secunderabad'],
        'Punjab': ['punjab', 'chandigarh', 'ludhiana', 'amritsar'],
        'Madhya Pradesh': ['madhya pradesh', 'bhopal', 'indore', 'gwalior'],
        'Bihar': ['bihar', 'patna'],
    }
    text_lower = text.lower()
    for state, keywords in states.items():
        if any(kw in text_lower for kw in keywords):
            return state
    return "Pan India"

def detect_city(text):
    """Detect city from text."""
    cities = {
        'Ahmedabad': 'ahmedabad', 'Surat': 'surat', 'Gandhinagar': 'gandhinagar',
        'Vadodara': 'vadodara', 'Rajkot': 'rajkot', 'Mumbai': 'mumbai',
        'Pune': 'pune', 'New Delhi': 'new delhi', 'Delhi': 'delhi',
        'Bengaluru': 'bengaluru', 'Chennai': 'chennai', 'Hyderabad': 'hyderabad',
        'Kolkata': 'kolkata', 'Jaipur': 'jaipur', 'Lucknow': 'lucknow',
        'Noida': 'noida', 'Bhopal': 'bhopal', 'Patna': 'patna',
    }
    text_lower = text.lower()
    for city, kw in cities.items():
        if kw in text_lower:
            return city
    return ""

def detect_category(title, quantity):
    """Detect service category and employee count from title."""
    title_lower = title.lower()
    employees = 0

    # Try to extract employee count from quantity
    try:
        nums = re.findall(r'\d+', str(quantity))
        if nums:
            employees = int(nums[0])
    except:
        pass

    # ── Specific Service Categories ──
    if any(kw in title_lower for kw in ['security guard', 'security personnel', 'security staff', 'security service', 'guard service', 'armed guard', 'unarmed guard', 'watch and ward']):
        return "SECURITY", employees

    if any(kw in title_lower for kw in ['housekeeping', 'house keeping', 'cleaning', 'sanitation', 'janitorial', 'sweeping', 'disinfection', 'laundry', 'horticulture', 'gardening']):
        return "HOUSEKEEPING", employees

    if any(kw in title_lower for kw in ['data entry', 'data entry operator', 'deo', 'data operator', 'computer operator']):
        return "DATA_ENTRY", employees

    if any(kw in title_lower for kw in ['driver', 'chauffeur', 'vehicle operator', 'lmv driver', 'hmv driver']):
        return "DRIVER", employees

    if any(kw in title_lower for kw in ['it manpower', 'it staff', 'software engineer', 'system administrator', 'network engineer', 'it support', 'it technician', 'hardware engineer']):
        return "IT_MANPOWER", employees

    if any(kw in title_lower for kw in ['electrician', 'electrical technician', 'electrical maintenance', 'electrical work']):
        return "ELECTRICIAN", employees

    if any(kw in title_lower for kw in ['helper', 'peon', 'attender', 'attendant', 'office assistant', 'multi tasking', 'mts', 'sweeper', 'unskilled']):
        return "HELPER", employees

    if any(kw in title_lower for kw in ['facility management', 'facility services', 'integrated facility', 'soft service', 'hard service', 'cafeteria', 'canteen']):
        return "FACILITY_MGMT", employees

    if any(kw in title_lower for kw in ['outsourcing', 'manpower outsourcing', 'contract staffing', 'third party', 'labour contract', 'labour supply', 'skilled labour', 'unskilled labour', 'skilled worker', 'manpower supply']):
        return "OUTSOURCING", employees

    # General manpower fallback
    if any(kw in title_lower for kw in ['manpower', 'staff', 'staffing', 'operator', 'worker', 'labour', 'personnel', 'workforce']):
        return "MANPOWER", employees

    if any(kw in title_lower for kw in ['it ', 'software', 'hardware', 'computer', 'networking', 'server', 'cloud', 'cyber', 'digital', 'technology', 'laptop', 'printer']):
        return "IT", employees

    return "OTHER", employees

def generate_ai_summary(title, category, employees, state):
    """Generate a concise AI-style summary for the bid."""
    emp_str = f"Min. {employees} personnel required." if employees else "Check doc for headcount."
    summaries = {
        "SECURITY":      f"Security guard contract in {state}. {emp_str} Ensure PSARA license, ESI/PF compliance, and uniform provision. MSME exemption may apply for small firms.",
        "HOUSEKEEPING":  f"Housekeeping/cleaning contract in {state}. {emp_str} ISO 9001 or equivalent preferred. Check for bio-medical clauses if hospital-related. Low EMD typical.",
        "DATA_ENTRY":    f"Data Entry Operator contract in {state}. {emp_str} Typing speed & accuracy tests expected. Verify IT infrastructure requirements in bid doc.",
        "DRIVER":        f"Driver/chauffeur contract in {state}. {emp_str} Valid LMV/HMV license mandatory. Check vehicle type, shift hours, and fuel responsibility clause.",
        "IT_MANPOWER":   f"IT manpower contract in {state}. {emp_str} OEM/technical certifications likely required. Verify NDA/data-security compliance requirements.",
        "ELECTRICIAN":   f"Electrical maintenance contract in {state}. {emp_str} Licensed electricians (ITI/Wireman cert) mandatory. Check safety compliance and shift patterns.",
        "HELPER":        f"Helper/support staff contract in {state}. {emp_str} Low skill threshold. Verify PF/ESI contributions and minimum wage compliance per state norms.",
        "FACILITY_MGMT": f"Integrated facility management contract in {state}. {emp_str} Multi-service scope – verify AMC, SLA terms and EPFO compliance across all sub-services.",
        "OUTSOURCING":   f"Manpower outsourcing contract in {state}. {emp_str} Third-party staffing model. Ensure labor law compliance, PF/ESI contributions, and exit clause clarity.",
        "MANPOWER":      f"General manpower requirement in {state}. {emp_str} Verify EPFO/ESI compliance and local labor regulations before bidding.",
        "IT":            f"IT procurement in {state}. OEM authorization and turnover criteria expected. Competitive category – ensure spec compliance.",
        "OTHER":         f"General service tender in {state}. Review eligibility criteria carefully before applying.",
    }
    return summaries.get(category, summaries["OTHER"])

def gem_live_scraper(filter_state=None, target_date=None):
    """
    Live scraper: uses fast AJAX requests from within a single headless Chrome session.
    """
    global scanned_bids, is_scanning, last_scan_time, scan_error
    is_scanning = True
    scan_error = None
    driver = None

    try:
        logging.info("[*] Starting fast live GeM scan via AJAX...")
        driver = get_chrome_driver()
        
        # Determine target date string in GeM's DD/MM/YYYY format
        if target_date:
            parts = target_date.split('-')
            if len(parts) == 3:
                today_str = f"{parts[2]}/{parts[1]}/{parts[0]}"
            else:
                today_str = time.strftime('%d/%m/%Y')
        else:
            today_str = time.strftime('%d/%m/%Y')

        # Load GeM page to initialize session and extract CSRF
        driver.get("https://bidplus.gem.gov.in/bidlists")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "block_header"))
        )
        time.sleep(2)

        # Extract CSRF credentials
        src = driver.page_source
        soup = BeautifulSoup(src, 'html.parser')
        csrf_name_el = soup.find('input', {'id': 'cname'})
        csrf_hash_el = soup.find('input', {'id': 'chash'})
        csrf_name = csrf_name_el.get('value', 'csrf_bd_gem_nk') if csrf_name_el else 'csrf_bd_gem_nk'
        csrf_hash = csrf_hash_el.get('value', '') if csrf_hash_el else ''

        logging.info(f"[*] Extracted CSRF Name: {csrf_name}, Hash: {csrf_hash}")

        # Call the API from within Chrome using JavaScript fetch
        result = driver.execute_async_script("""
        var callback = arguments[arguments.length - 1];
        var csrfName = arguments[0];
        var csrfHash = arguments[1];
        var filterState = arguments[2];
        var targetDate = arguments[3];

        var allDocs = [];
        var maxPages = 15;

        async function fetchPage(pageNum) {
            var postdata = {
                page: pageNum,
                param: {
                    searchBid: filterState || "",
                    searchType: "fullText"
                },
                filter: {
                    bidStatusType: "ongoing_bids",
                    byType: "all",
                    highBidValue: "",
                    byEndDate: { from: "", to: "" },
                    sort: "Bid-Start-Date-Latest"
                }
            };
            
            var formData = new URLSearchParams();
            formData.append('payload', JSON.stringify(postdata));
            formData.append(csrfName, csrfHash);
            
            var bodyString = formData.toString();
            if (targetDate) {
                bodyString += '&bidStartDate=' + targetDate;
                try {
                    var parts = targetDate.split('/');
                    var d = new Date(parseInt(parts[2]), parseInt(parts[1]) - 1, parseInt(parts[0]));
                    d.setDate(d.getDate() + 30);
                    var dd = String(d.getDate()).padStart(2, '0');
                    var mm = String(d.getMonth() + 1).padStart(2, '0');
                    var yyyy = d.getFullYear();
                    var futureDateStr = dd + '/' + mm + '/' + yyyy;
                    bodyString += '&bidEndDate=' + futureDateStr;
                } catch(e) {
                    bodyString += '&bidEndDate=' + targetDate;
                }
            }

            try {
                let response = await fetch('/all-bids-data', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: bodyString
                });
                let data = await response.json();
                return data.response?.response?.docs || [];
            } catch (e) {
                console.error("Fetch page " + pageNum + " failed:", e);
                return [];
            }
        }

        async function fetchAll() {
            for (let p = 1; p <= maxPages; p++) {
                let docs = await fetchPage(p);
                if (!docs || docs.length === 0) {
                    break;
                }
                allDocs = allDocs.concat(docs);
                if (docs.length < 10) {
                    break;
                }
                await new Promise(resolve => setTimeout(resolve, 100));
            }
            callback({ success: true, docs: allDocs });
        }

        fetchAll().catch(e => callback({ success: false, error: e.toString() }));
        """, csrf_name, csrf_hash, filter_state, today_str)

        if result and result.get('success'):
            raw_docs = result.get('docs', [])
            logging.info(f"[*] API returned {len(raw_docs)} ongoing bids.")
            all_bids = parse_json_docs(raw_docs, filter_state=filter_state, status_type='published')
        else:
            raise Exception(result.get('error', 'Unknown JavaScript execution error'))

        # DEDUPLICATE by bid ID
        seen_ids = set()
        unique_bids = []
        for bid in all_bids:
            if bid['id'] not in seen_ids:
                seen_ids.add(bid['id'])
                unique_bids.append(bid)
        
        scanned_bids = unique_bids
        last_scan_time = time.strftime('%Y-%m-%d %H:%M:%S')
        last_scan_date = target_date or time.strftime('%Y-%m-%d')
        logging.info(f"[✓] Published scan done. Total: {len(scanned_bids)} unique bids for date {last_scan_date}.")

    except Exception as e:
        scan_error = str(e)
        logging.error(f"[!] Published scan failed: {e}")
    finally:
        if driver:
            driver.quit()
        is_scanning = False

def gem_finished_scraper(filter_state=None, target_date=None):
    """
    Scraper for finished bids using fast AJAX requests inside a single headless Chrome session.
    """
    global scanned_bids, is_scanning, last_scan_time, scan_error
    is_scanning = True
    scan_error = None
    driver = None

    try:
        logging.info("[*] Starting fast live GeM scan for FINISHED bids...")
        driver = get_chrome_driver()

        # Load page to initialize session cookies and CSRF
        driver.get("https://bidplus.gem.gov.in/bidlists")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "block_header"))
        )
        time.sleep(2)

        # Extract CSRF credentials
        src = driver.page_source
        soup = BeautifulSoup(src, 'html.parser')
        csrf_name_el = soup.find('input', {'id': 'cname'})
        csrf_hash_el = soup.find('input', {'id': 'chash'})
        csrf_name = csrf_name_el.get('value', 'csrf_bd_gem_nk') if csrf_name_el else 'csrf_bd_gem_nk'
        csrf_hash = csrf_hash_el.get('value', '') if csrf_hash_el else ''

        logging.info(f"[*] Extracted CSRF Name: {csrf_name}, Hash: {csrf_hash}")

        # GeM API accepts YYYY-MM-DD or DD-MM-YYYY format for byEndDate in JSON payload
        if target_date:
            gem_date_str = target_date
        else:
            gem_date_str = time.strftime('%Y-%m-%d')

        logging.info(f"[*] Fetching bids ending on: {gem_date_str}")

        # Execute async batch fetch inside browser
        result = driver.execute_async_script("""
        var callback = arguments[arguments.length - 1];
        var csrfName = arguments[0];
        var csrfHash = arguments[1];
        var filterState = arguments[2];
        var gemDateStr = arguments[3];  // DD/MM/YYYY for byEndDate filter

        var finishedDocs = [];
        var ongoingDocs = [];
        var maxPages = 15;

        async function fetchPage(pageNum, isFinished) {
            var postdata = {
                page: pageNum,
                param: {
                    searchBid: filterState || "",
                    searchType: "fullText"
                },
                filter: {
                    bidStatusType: isFinished ? "bidrastatus" : "ongoing_bids",
                    byType: "all",
                    highBidValue: "",
                    byEndDate: gemDateStr
                        ? { from: gemDateStr, to: gemDateStr }
                        : { from: "", to: "" },
                    sort: isFinished ? "Bid-End-Date-Latest" : "Bid-End-Date-Oldest"
                }
            };
            
            var formData = new URLSearchParams();
            formData.append('payload', JSON.stringify(postdata));
            formData.append(csrfName, csrfHash);
            
            try {
                let response = await fetch('/all-bids-data', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: formData.toString()
                });
                let data = await response.json();
                return data.response?.response?.docs || [];
            } catch (e) {
                console.error("Fetch page " + pageNum + " failed:", e);
                return [];
            }
        }

        async function fetchAll() {
            // 1. Fetch finished bids ending on selected date
            for (let p = 1; p <= maxPages; p++) {
                let docs = await fetchPage(p, true);
                if (!docs || docs.length === 0) break;
                finishedDocs = finishedDocs.concat(docs);
                if (docs.length < 10) break;
                await new Promise(resolve => setTimeout(resolve, 100));
            }

            // 2. Fetch ongoing bids ending on selected date
            for (let p = 1; p <= maxPages; p++) {
                let docs = await fetchPage(p, false);
                if (!docs || docs.length === 0) break;
                ongoingDocs = ongoingDocs.concat(docs);
                if (docs.length < 10) break;
                await new Promise(resolve => setTimeout(resolve, 100));
            }
            
            callback({ success: true, finished_docs: finishedDocs, ongoing_docs: ongoingDocs });
        }

        fetchAll().catch(e => callback({ success: false, error: e.toString() }));
        """, csrf_name, csrf_hash, filter_state, gem_date_str)

        if result and result.get('success'):
            finished_raw = result.get('finished_docs', [])
            ongoing_raw = result.get('ongoing_docs', [])
            logging.info(f"[*] API returned {len(finished_raw)} finished and {len(ongoing_raw)} ongoing bids.")
            
            finished_bids = parse_json_docs(finished_raw, filter_state=filter_state, status_type='finished')
            ongoing_bids = parse_json_docs(ongoing_raw, filter_state=filter_state, status_type='ongoing')
            
            all_bids = finished_bids + ongoing_bids
        else:
            raise Exception(result.get('error', 'Unknown JavaScript execution error'))

        # DEDUPLICATE only — date filtering is handled on the frontend
        seen_ids = set()
        unique_bids = []
        for bid in all_bids:
            if bid['id'] not in seen_ids:
                seen_ids.add(bid['id'])
                unique_bids.append(bid)

        scanned_bids = unique_bids
        last_scan_time = time.strftime('%Y-%m-%d %H:%M:%S')
        last_scan_date = target_date or time.strftime('%Y-%m-%d')
        logging.info(f"[✓] Finished scan complete. Total: {len(scanned_bids)} unique bids for date {last_scan_date}.")

    except Exception as e:
        scan_error = str(e)
        logging.error(f"[!] Finished scan failed: {e}")
    finally:
        if driver:
            driver.quit()
        is_scanning = False

# ─── Flask Routes ──────────────────────────────────────────────────────────

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

@app.route('/api/bids', methods=['GET'])
def get_bids():
    return jsonify({
        "status": "success",
        "last_scan": last_scan_time,
        "scan_date": last_scan_date,
        "is_scanning": is_scanning,
        "scan_error": scan_error,
        "total": len(scanned_bids),
        "data": scanned_bids
    })

@app.route('/api/scan', methods=['POST'])
def trigger_scan():
    global is_scanning
    if is_scanning:
        return jsonify({"status": "in_progress", "message": "A live GeM scan is already running."}), 429

    body = request.get_json(silent=True) or {}
    scan_type = body.get('type', 'published')   # 'published' or 'finished'
    state_filter = body.get('state', None)       # e.g. 'Gujarat'
    target_date = body.get('date', None)         # e.g. '2026-05-15'

    if scan_type == 'finished':
        thread = threading.Thread(target=gem_finished_scraper, args=(state_filter, target_date))
    else:
        thread = threading.Thread(target=gem_live_scraper, args=(state_filter, target_date))

    thread.daemon = True
    thread.start()

    return jsonify({
        "status": "scanning",
        "message": f"Live Chrome scan started on official GeM portal. Scanning '{scan_type}' bids.",
        "type": scan_type
    }), 202

@app.route('/api/status', methods=['GET'])
def scan_status():
    return jsonify({
        "is_scanning": is_scanning,
        "last_scan": last_scan_time,
        "scan_date": last_scan_date,
        "total_bids": len(scanned_bids),
        "error": scan_error
    })

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 8080))
    print("=" * 60)
    print("  GeM Intelligence - Professional Monitoring Server")
    print("=" * 60)
    print(f"  Server: http://localhost:{port}")
    print(f"  API:    http://localhost:{port}/api/bids")
    print(f"  Scan:   POST http://localhost:{port}/api/scan")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
