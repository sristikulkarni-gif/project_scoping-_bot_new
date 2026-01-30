import requests
import json

HOST = "http://localhost:11434"
MODEL = "nomic-embed-text"

def test_embed():
    url = f"{HOST}/api/embed"
    
    # Test 1: Single string in list (Standard case)
    payload1 = {
        "model": MODEL,
        "input": ["Hello world"]
    }
    print(f"\nTest 1: Single list input -> {payload1}")
    resp1 = requests.post(url, json=payload1)
    print(f"Status: {resp1.status_code}")
    if resp1.status_code != 200:
        print(f"Response: {resp1.text}")
    else:
        print("Success")

    # Test 2: Single string (Not list) - Some versions might dislike this
    payload2 = {
        "model": MODEL,
        "input": "Hello world"
    }
    print(f"\nTest 2: Raw string input -> {payload2}")
    resp2 = requests.post(url, json=payload2)
    print(f"Status: {resp2.status_code}")
    if resp2.status_code != 200:
        print(f"Response: {resp2.text}")
    else:
        print("Success")

    # Test 3: Empty list
    payload3 = {
        "model": MODEL,
        "input": []
    }
    print(f"\nTest 3: Empty list -> {payload3}")
    resp3 = requests.post(url, json=payload3)
    print(f"Status: {resp3.status_code}")
    
    # Test 4: List with empty string
    payload4 = {
        "model": MODEL,
        "input": [""]
    }
    print(f"\nTest 4: List with empty string -> {payload4}")
    resp4 = requests.post(url, json=payload4)
    print(f"Status: {resp4.status_code}")
    if resp4.status_code != 200:
        print(f"Response: {resp4.text}")

if __name__ == "__main__":
    test_embed()
