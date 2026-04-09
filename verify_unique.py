import requests
import json

BASE_URL = "http://localhost:8000/api"

def test_unique_predictions():
    # We use some real IDs if possible, or just different team names
    payload = {
        "matches": [
            {
                "home_team": "Arsenal",
                "away_team": "Luton",
                "home_team_id": "57", # Arsenal
                "away_team_id": "389", # Luton
                "home_position": 1,
                "away_position": 18,
                "competition_code": "PL"
            },
            {
                "home_team": "Manchester City",
                "away_team": "Aston Villa",
                "home_team_id": "65", # City
                "away_team_id": "58", # Villa
                "home_position": 2,
                "away_position": 4,
                "competition_code": "PL"
            }
        ]
    }

    print("Sending batch prediction request...")
    response = requests.post(f"{BASE_URL}/predict/batch", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        results = data['results']
        
        p1 = results[0]['match_result']
        p2 = results[1]['match_result']
        
        print(f"Match 1 (Arsenal v Luton): {p1}")
        print(f"Match 2 (City v Villa): {p2}")
        
        if p1 == p2:
            print("❌ FAILURE: Predictions are still identical!")
        else:
            print("✅ SUCCESS: Predictions are unique!")
    else:
        print(f"FAILED! Status: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_unique_predictions()
