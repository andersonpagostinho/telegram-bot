#!/usr/bin/env python3
"""Test if JSONResponse.set_cookie() works in Uvicorn."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/test-cookie")
def test_cookie():
    """Simple endpoint to test if set_cookie works."""
    resp = JSONResponse({"message": "hello"})
    resp.set_cookie(
        key="test_cookie",
        value="test_value_12345",
        httponly=True,
        secure=False,
        samesite="Lax",
    )
    return resp

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
