import requests

try:
    print("Testing /api/case_studies/pending endpoint...")
    response = requests.get("http://localhost:8000/api/case_studies/pending")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:200]}")
    
    if response.status_code == 404:
        print("❌ Endpoint not found!")
    elif response.status_code == 401:
        print("✅ Endpoint exists (Auth required)")
    elif response.status_code == 200:
        print("✅ Endpoint working!")
    else:
        print(f"⚠️ Unexpected status: {response.status_code}")

except Exception as e:
    print(f"❌ Connection failed: {e}")
