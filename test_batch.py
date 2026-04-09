import requests
import json

BASE_URL = "http://localhost:8000/api"

def test_batch_prediction():
    payload = {
        "matches": [
            {
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "home_position": 1,
                "away_position": 10,
                "competition_code": "PL",
                "home_lineup": [],
                "away_lineup": []
            },
            {
                "home_team": "Liverpool",
                "away_team": "Everton",
                "home_position": 2,
                "away_position": 15,
                "competition_code": "PL",
                "home_lineup": [],
                "away_lineup": []
            }
        ]
    }

    print("Sending batch prediction request...")
    response = requests.post(f"{BASE_URL}/predict/batch", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"SUCCESS! Batch ID: {data['batch_id']}")
        print(f"Total: {data['total']}, Successful: {data['successful']}, Failed: {data['failed']}")
        return data['batch_id']
    else:
        print(f"FAILED! Status: {response.status_code}")
        print(response.text)
        return None

def test_batch_export(batch_id):
    if not batch_id: return
    print(f"Testing export for batch {batch_id}...")
    response = requests.get(f"{BASE_URL}/export/batch/{batch_id}")
    if response.status_code == 200:
        print("SUCCESS! Export received.")
        with open("test_batch_export.xlsx", "wb") as f:
            f.write(response.content)
        print("Saved to test_batch_export.xlsx")
    else:
        print(f"FAILED! Status: {response.status_code}")

if __name__ == "__main__":
    bid = test_batch_prediction()
    if bid:
        test_batch_export(bid)
