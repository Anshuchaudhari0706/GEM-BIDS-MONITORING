import cloudscraper
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings()

scraper = cloudscraper.create_scraper()

url = "https://bidplus.gem.gov.in/bidlists"
print("Fetching with cloudscraper...")
response = scraper.get(url)
print("Status:", response.status_code)
if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    bids = soup.find_all('div', class_='border block')
    print(f"Found {len(bids)} bids")
    if bids:
        print(bids[0].text[:300].strip())
else:
    print("Failed")
