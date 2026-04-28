import urllib.request
import urllib.error
import json

url = "http://localhost:8000/mcp/execute"

# Test 1: Approved action
print("=== Test 1: Approved restart ===")
try:
    req = urllib.request.Request(url, data=json.dumps({"prompt": "restart service-a"}).encode(), headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req)
    print(resp.read().decode())
except urllib.error.HTTPError as e:
    print(f"ERROR {e.code}: {e.read().decode()}")

# Test 2: Rejected action
print("\n=== Test 2: Rejected restart ===")
try:
    req = urllib.request.Request(url, data=json.dumps({"prompt": "reject restart of service-b"}).encode(), headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req)
    print(resp.read().decode())
except urllib.error.HTTPError as e:
    print(f"ERROR {e.code}: {e.read().decode()}")

# Test 3: View audit logs
print("\n=== Audit Logs ===")
try:
    resp = urllib.request.urlopen("http://localhost:8000/audit/")
    logs = json.loads(resp.read().decode())
    for log in logs:
        print(json.dumps(log, indent=2))
except urllib.error.HTTPError as e:
    print(f"ERROR {e.code}: {e.read().decode()}")
