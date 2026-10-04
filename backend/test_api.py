import requests
import json

# Step 1: Start a new scan
print("Step 1: Starting scan...")
scan_url = "http://127.0.0.1:8000/scan/start"
scan_data = {"folder_path": "C:\\1photo"}
scan_response = requests.post(scan_url, json=scan_data)
print(f"Scan Status: {scan_response.status_code}")
scan_result = scan_response.json()
print(json.dumps(scan_result, indent=2))

# Extract scan_id
scan_id = scan_result.get("scan_id")
if not scan_id:
    print("ERROR: No scan_id returned!")
    exit(1)

print(f"\n✓ Scan ID: {scan_id}")

# Step 2: Get detailed results
print("\nStep 2: Fetching detailed results...")
results_url = f"http://127.0.0.1:8000/scan/results?scan_id={scan_id}"
results_response = requests.get(results_url)
print(f"Results Status: {results_response.status_code}")
print(json.dumps(results_response.json(), indent=2))
