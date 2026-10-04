import requests
import json

url = 'http://127.0.0.1:8000/scan/start'
folder = r'C:\test_photos'
params = {'folder_path': folder}

print('Starting scan from:', folder)
response = requests.post(url, params=params)
result = response.json()
print(json.dumps(result, indent=2))