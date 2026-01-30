"""
Vercel Serverless Function - Main API entry point.
This file exposes the FastAPI app for Vercel's Python runtime.
"""
import sys
from pathlib import Path

# Add the project root to the path so we can import the backend
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from backend.app.main import app as backend_app

# Create a wrapper app that strips /api prefix
app = FastAPI()

class StripApiPrefixMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Strip /api prefix from path if present
        if request.scope["path"].startswith("/api"):
            request.scope["path"] = request.scope["path"][4:] or "/"
            if request.scope.get("raw_path"):
                raw_path = request.scope["raw_path"].decode()
                if raw_path.startswith("/api"):
                    request.scope["raw_path"] = (raw_path[4:] or "/").encode()
        return await call_next(request)

# Add the middleware to the backend app
backend_app.add_middleware(StripApiPrefixMiddleware)

# Export the backend app with middleware
app = backend_app
