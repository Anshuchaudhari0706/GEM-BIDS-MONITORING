import requests
import time

def run():
    print("Starting scan via API...")
    try:
        r = requests.post("http://localhost:8080/api/scan", json={
            "type": "published",
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
        if bids.get("data"):
            print("First bid title:", bids["data"][0]["title"])
            print("First bid state:", bids["data"][0]["state"])
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    run()
