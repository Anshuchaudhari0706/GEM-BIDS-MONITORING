import requests
import time

def run():
    print("Starting finished scan via API...")
    try:
        r = requests.post("http://localhost:8080/api/scan", json={
            "type": "finished",
            "state": "Gujarat",
            "date": time.strftime('%Y-%m-%d')
        })
        print("Trigger Response:", r.json())
        
        while True:
            time.sleep(3)
            status = requests.get("http://localhost:8080/api/status").json()
            if status.get("is_scanning"):
                print(f"Scanning... {status.get('total_bids', 0)} bids so far")
            else:
                print("Scan finished!")
                print("Final Status:", status)
                break
                
        bids = requests.get("http://localhost:8080/api/bids").json()
        print("Total bids received:", bids.get("total"))
        data = bids.get("data", [])
        
        finished_count = sum(1 for b in data if b.get('status') == 'finished')
        ongoing_count = sum(1 for b in data if b.get('status') == 'ongoing')
        print(f"Bids with status 'finished': {finished_count}")
        print(f"Bids with status 'ongoing': {ongoing_count}")
        
        if data:
            print("\nSample bids:")
            for b in data[:5]:
                print(f"- ID: {b['id']}, Status: {b['status']}, Title: {b['title'][:50]}, End Date: {b.get('rawEndDate', b.get('deadline'))}")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    run()
