import requests
from bs4 import BeautifulSoup

url = "https://bidplus.gem.gov.in/all-bids"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
response = requests.get(url, headers=headers)
print(response.status_code)
if response.status_code == 200:
    soup = BeautifulSoup(response.content, 'html.parser')
    print(soup.text[:2000])
