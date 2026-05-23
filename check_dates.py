from bs4 import BeautifulSoup
import time

with open('gem_source2.html', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')
cards = soup.find_all('div', class_='card')
today = time.strftime('%d-%m-%Y')
print(f'Today: {today}')
print(f'Total cards: {len(cards)}')
print()
for i, card in enumerate(cards[:10]):
    start = card.find('span', class_='start_date')
    end = card.find('span', class_='end_date')
    bid = card.find('a', class_='bid_no_hover')
    bid_id = bid.get_text(strip=True) if bid else "?"
    start_date = start.get_text(strip=True) if start else "?"
    end_date = end.get_text(strip=True) if end else "?"
    today_match = "TODAY" if today in start_date else ""
    print(f"Bid: {bid_id} | Start: {start_date} | End: {end_date} {today_match}")
