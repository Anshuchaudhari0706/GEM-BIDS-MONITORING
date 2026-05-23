import requests
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings()

url = "https://bidplus.gem.gov.in/bidlists"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

print("Fetching URL:", url)
response = requests.get(url, headers=headers, verify=False)
print("Status Code:", response.status_code)

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    # Bids are usually in 'div' with class 'border block'
    bids = soup.find_all('div', class_='border block')
    print(f"Found {len(bids)} bids")
    
    for i, bid in enumerate(bids[:3]):
        print(f"\n--- BID {i+1} ---")
        print(bid.text.strip()[:300].replace('\n', ' '))
else:
    print("Failed to fetch.")
