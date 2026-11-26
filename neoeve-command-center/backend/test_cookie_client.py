#!/usr/bin/env python3
"""Test if cookies are being set correctly by the main app."""

import requests
import http.cookiejar

# Create a session with cookie jar to capture cookies
session = requests.Session()
jar = http.cookiejar.CookieJar()
session.cookies = jar

print("=" * 60)
print("Testing login endpoint for Set-Cookie")
print("=" * 60)

r = session.post(
    'http://localhost:8000/api/v1/auth/login',
    json={'email': 'admin@test.com', 'password': 'Admin123!'},
    timeout=5
)

print(f"\nStatus: {r.status_code}")
print(f"\nResponse headers:")
for key, value in r.headers.items():
    if key.lower() in ['set-cookie', 'content-type', 'content-length']:
        print(f"  {key}: {value}")

print(f"\nSet-Cookie in headers: {'Set-Cookie' in r.headers}")
print(f"Set-Cookie in raw headers: {'set-cookie' in r.headers}")

# Check if any cookies were captured
print(f"\nCookies captured by session:")
if session.cookies:
    for cookie in session.cookies:
        print(f"  - {cookie.name}: {cookie.value[:20]}... (HttpOnly: {cookie.has_nonstandard_attr('HttpOnly')})")
else:
    print(f"  NONE!")

# Try to show raw response headers
print(f"\nRaw response (first 500 chars):")
print(r.text[:500])
