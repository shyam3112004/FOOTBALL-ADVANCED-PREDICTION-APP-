import requests
import json

try:
    resp = requests.get("http://localhost:8000/api/competitions")
    print(f"Status: {resp.status_code}")
    data = resp.json()
    print(f"Type: {type(data)}")
    if isinstance(data, list):
        print(f"Length: {len(data)}")
        if len(data) > 0:
            print(f"First element: {json.dumps(data[0], indent=2)}")
    else:
        print(f"Content: {json.dumps(data, indent=2)}")
except Exception as e:
    print(f"Error: {e}")
