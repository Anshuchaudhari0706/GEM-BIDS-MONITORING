import requests
import time

print("Triggering live scan on GeM portal...")
r = requests.post('http://localhost:8080/api/scan', json={'type': 'published', 'state': None})
print("Response:", r.json())
print()

for i in range(24):
    time.sleep(5)
    s = requests.get('http://localhost:8080/api/status').json()
    scanning = s['is_scanning']
    total = s['total_bids']
    err = s.get('error') or s.get('scan_error')
    print(f"[{i+1:02d}] scanning={scanning} | bids_found={total} | error={err}")
    if not scanning:
        print("\nScan complete!")
        bids = requests.get('http://localhost:8080/api/bids').json()
        print(f"Total bids: {bids['total']}")
        for b in bids['data'][:5]:
            print(f"  {b['id']} | {b['title'][:60]} | Start: {b['rawStartDate']}")
        break
