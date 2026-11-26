import requests
import json

r = requests.post('http://localhost:8000/api/v1/auth/login', json={'email': 'admin@test.com', 'password': 'Admin123!'})

print(f"Status: {r.status_code}")
print(f"Response headers: {dict(r.headers)}")
print(f"Response cookies: {dict(r.cookies)}")
print(f"Set-Cookie in headers: {'set-cookie' in r.headers}")

if r.status_code == 200:
    data = r.json()
    print(f"\nResponse data keys: {list(data.keys())}")
    print(f"access_token: {data.get('access_token', 'MISSING')[:50]}...")
    print(f"token_type: {data.get('token_type')}")
    print(f"\n✅ Login successful!")
