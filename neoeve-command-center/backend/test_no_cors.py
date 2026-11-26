#!/usr/bin/env python3
"""Test if cookies work WITHOUT CORS middleware."""

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse

app = FastAPI()

@app.post("/test-cookie-no-cors")
def test_with_response(response: Response):
    """Test with response param, NO CORS."""
    response.set_cookie(
        key="test_cookie",
        value="test_value_12345",
        httponly=True,
        secure=False,
        samesite="Lax",
    )
    return JSONResponse({"message": "hello"})

@app.post("/test-manual-header")
def test_with_header():
    """Test with manual header, NO CORS."""
    return JSONResponse(
        {"message": "hello"},
        headers={"Set-Cookie": "manual_cookie=manual_value_123; HttpOnly; SameSite=Lax"}
    )

if __name__ == "__main__":
    import uvicorn
    import requests

    # Start server in background
    import subprocess
    import time
    import sys

    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "test_no_cors:app", "--host", "127.0.0.1", "--port", "8002"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    time.sleep(2)

    try:
        print("=" * 60)
        print("Test 1: response.set_cookie() NO CORS")
        print("=" * 60)
        r = requests.post("http://127.0.0.1:8002/test-cookie-no-cors")
        print(f"Status: {r.status_code}")
        print(f"Set-Cookie in headers: {'set-cookie' in r.headers}")
        if 'set-cookie' in r.headers:
            print(f"Set-Cookie value: {r.headers['set-cookie']}")

        print("\n" + "=" * 60)
        print("Test 2: Manual header NO CORS")
        print("=" * 60)
        r = requests.post("http://127.0.0.1:8002/test-manual-header")
        print(f"Status: {r.status_code}")
        print(f"Set-Cookie in headers: {'set-cookie' in r.headers}")
        if 'set-cookie' in r.headers:
            print(f"Set-Cookie value: {r.headers['set-cookie']}")
    finally:
        server.terminate()
        server.wait()
