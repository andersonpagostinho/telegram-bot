#!/usr/bin/env python3
"""Test login via HTTP with detailed error info."""

import requests
import json
import sys

url = "http://localhost:8000/api/v1/auth/login"
payload = {"email": "admin@test.com", "password": "Admin123!"}

print("=" * 60)
print("Testing HTTP Login")
print("=" * 60)

try:
    print(f"\n📤 Sending POST to {url}")
    print(f"   Payload: {payload}")

    response = requests.post(url, json=payload, timeout=5)

    print(f"\n📥 Response received:")
    print(f"   Status Code: {response.status_code}")
    print(f"   Headers: {dict(response.headers)}")
    print(f"\n   Body:")
    print(f"   {response.text}")

    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Success!")
        print(f"   Access Token: {data.get('access_token', 'MISSING')[:50]}...")
        print(f"   Token Type: {data.get('token_type')}")

        # Check cookies
        cookies = response.cookies
        print(f"\n   Cookies set: {list(cookies.keys())}")
        for key, value in cookies.items():
            print(f"     - {key}: {value[:20]}...")
    else:
        print(f"\n❌ Error {response.status_code}")
        try:
            error_data = response.json()
            print(f"   Error detail: {error_data.get('detail')}")
        except:
            print(f"   Raw error: {response.text}")

except Exception as e:
    print(f"\n❌ Exception: {type(e).__name__}: {str(e)}")
    sys.exit(1)
