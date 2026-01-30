"""
Vercel Serverless Function - Main API entry point.
This file exposes the FastAPI app for Vercel's Python runtime.
"""
import sys
import json
import time
from pathlib import Path

# #region agent log
LOG_PATH = "/Users/dhruvghosh/Desktop/proj/.cursor/debug.log"
def _debug_log(location, message, data, hypothesis_id):
    try:
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps({"location": location, "message": message, "data": data, "timestamp": int(time.time()*1000), "sessionId": "debug-session", "hypothesisId": hypothesis_id}) + "\n")
    except: pass
# #endregion

# Add the project root to the path so we can import the backend
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# #region agent log
_debug_log("api/index.py:import", "Starting imports", {"project_root": str(project_root)}, "B")
# #endregion

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# #region agent log
_debug_log("api/index.py:import", "Importing backend app", {}, "B")
# #endregion

from backend.app.main import app as backend_app

# #region agent log
_debug_log("api/index.py:import", "Backend app imported successfully", {}, "B")
# #endregion

# Create a wrapper app that strips /api prefix
app = FastAPI()

class StripApiPrefixMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        original_path = request.scope["path"]
        # #region agent log
        _debug_log("api/index.py:middleware", "Request received", {"original_path": original_path, "method": request.method}, "C,D")
        # #endregion
        
        # Strip /api prefix from path if present
        if request.scope["path"].startswith("/api"):
            request.scope["path"] = request.scope["path"][4:] or "/"
            if request.scope.get("raw_path"):
                raw_path = request.scope["raw_path"].decode()
                if raw_path.startswith("/api"):
                    request.scope["raw_path"] = (raw_path[4:] or "/").encode()
        
        # #region agent log
        _debug_log("api/index.py:middleware", "Path after strip", {"original": original_path, "stripped": request.scope["path"]}, "D")
        # #endregion
        
        response = await call_next(request)
        
        # #region agent log
        _debug_log("api/index.py:middleware", "Response", {"status": response.status_code, "path": request.scope["path"]}, "C,D")
        # #endregion
        
        return response

# Add the middleware to the backend app
backend_app.add_middleware(StripApiPrefixMiddleware)

# Export the backend app with middleware
app = backend_app
