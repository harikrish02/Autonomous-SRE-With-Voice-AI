import httpx
import json
import os

key = os.getenv("GEMINI_API_KEY")
url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"
payload = {
    "contents": [{"parts": [{"text": "Return strictly valid JSON with keys action, service_name, replicas, approval_status for: restart service-b"}]}],
    "generationConfig": {"responseMimeType": "application/json"}
}
r = httpx.post(url, json=payload, headers={"X-goog-api-key": key, "Content-Type": "application/json"})
print("Status:", r.status_code)
print("Body:", r.text[:800])
