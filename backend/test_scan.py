import requests
import json

url = "http://127.0.0.1:8000/scan/start"
params = {"folder_path": r"C:\test_photos"}

print("Starting scan...")
response = requests.post(url, params=params)
result = response.json()

print("\n" + "="*60)
print("SCAN RESULTS")
print("="*60)
print(json.dumps(result, indent=2))
