"""
Vercel Serverless Function - Main API entry point.
This file exposes the FastAPI app for Vercel's Python runtime.
"""
import sys
from pathlib import Path

# Add the project root to the path so we can import the backend
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.app.main import app

# Vercel expects an 'app' export for FastAPI
# The app variable is automatically detected and used
