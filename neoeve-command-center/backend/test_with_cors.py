#!/usr/bin/env python3
"""Test if cookies work WITH CORS middleware."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()

# Add CORS middleware EXACTLY like main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/test-manual-header")
def test_with_header():
    """Test with manual Set-Cookie header WITH CORS."""
    return JSONResponse(
        {"message": "hello"},
        headers={"Set-Cookie": "manual_cookie=manual_value_123; HttpOnly; SameSite=Lax"}
    )

if __name__ == "__main__":
    import uvicorn
    import requests
    import subprocess
    import time
    import sys

    # Start server
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "test_with_cors:app", "--host", "127.0.0.1", "--port", "8003"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    time.sleep(2)

    try:
        print("=" * 60)
        print("Test: Manual header WITH CORS middleware")
        print("=" * 60)
        r = requests.post(
            "http://127.0.0.1:8003/test-manual-header",
            headers={"Origin": "http://localhost:5173"}  # Trigger CORS
        )
        print(f"Status: {r.status_code}")
        print(f"Set-Cookie in headers: {'set-cookie' in r.headers}")
        if 'set-cookie' in r.headers:
            print(f"✅ Set-Cookie value: {r.headers['set-cookie']}")
        else:
            print(f"❌ Set-Cookie NOT present (CORS filtered it)")
    finally:
        server.terminate()
        server.wait()
