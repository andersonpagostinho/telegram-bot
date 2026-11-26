import requests

session = requests.Session()

# Login
print("=" * 60)
print("1. Login")
print("=" * 60)

r = session.post('http://localhost:8000/api/v1/auth/login', json={'email': 'admin@test.com', 'password': 'Admin123!'})

print(f"Status: {r.status_code}")
print(f"Session cookies: {dict(session.cookies)}")

if r.status_code == 200:
    data = r.json()
    print(f"✅ Login successful!")
    print(f"   access_token: {data.get('access_token', 'MISSING')[:50]}...")
    print(f"   token_type: {data.get('token_type')}")

    # Try to get WebSocket ticket
    print("\n" + "=" * 60)
    print("2. Get WebSocket ticket")
    print("=" * 60)

    r2 = session.post(
        'http://localhost:8000/api/v1/websocket/ticket',
        headers={'Authorization': f"Bearer {data['access_token']}"}
    )

    print(f"Status: {r2.status_code}")
    if r2.status_code == 200:
        ticket = r2.json()
        print(f"✅ Ticket obtained!")
        print(f"   ticket: {ticket.get('ticket', 'MISSING')[:50]}...")
    else:
        print(f"❌ Error: {r2.text}")
