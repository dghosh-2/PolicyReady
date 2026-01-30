"""
Supabase Storage service for fetching PDFs and index data.
Uses direct HTTP requests to avoid heavy SDK dependencies.
"""
import os
import json
import tempfile
from functools import lru_cache
from typing import Optional
import httpx

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
BUCKET_NAME = "policyready"


def is_supabase_configured() -> bool:
    """Check if Supabase is configured for use."""
    return bool(SUPABASE_URL) and bool(SUPABASE_KEY)


def _get_storage_url(path: str = "") -> str:
    """Build Supabase Storage API URL."""
    base = f"{SUPABASE_URL}/storage/v1/object"
    if path:
        return f"{base}/{BUCKET_NAME}/{path}"
    return base


def _get_headers() -> dict:
    """Get auth headers for Supabase API."""
    return {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "apikey": SUPABASE_KEY,
    }


def get_index_json() -> Optional[dict]:
    """
    Fetch index.json from Supabase Storage.
    Returns the parsed JSON data or None if not available.
    """
    if not is_supabase_configured():
        return None
    
    try:
        url = _get_storage_url("index.json")
        response = httpx.get(url, headers=_get_headers(), timeout=30.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching index.json from Supabase: {e}")
        return None


def download_pdf_to_temp(folder: str, filename: str) -> Optional[str]:
    """
    Download a PDF from Supabase Storage to a temporary file.
    Returns the path to the temp file, or None if failed.
    """
    if not is_supabase_configured():
        return None
    
    try:
        # Path in storage: Public Policies/AA/filename.pdf
        storage_path = f"Public Policies/{folder}/{filename}"
        url = _get_storage_url(storage_path)
        response = httpx.get(url, headers=_get_headers(), timeout=60.0)
        response.raise_for_status()
        
        # Write to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp.write(response.content)
            return tmp.name
    except Exception as e:
        print(f"Error downloading PDF from Supabase: {e}")
        return None


def _list_storage_objects(prefix: str) -> list[dict]:
    """List objects in Supabase Storage with given prefix."""
    if not is_supabase_configured():
        return []
    
    try:
        url = f"{SUPABASE_URL}/storage/v1/object/list/{BUCKET_NAME}"
        response = httpx.post(
            url,
            headers=_get_headers(),
            json={"prefix": prefix, "limit": 1000},
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error listing objects from Supabase: {e}")
        return []


def list_policy_folders() -> list[dict]:
    """
    List all policy folders and their file counts from Supabase Storage.
    Returns list of {name, file_count} dicts.
    """
    items = _list_storage_objects("Public Policies/")
    
    # Group by folder
    folders = {}
    for item in items:
        name = item.get("name", "")
        # Skip the prefix folder itself
        if name == "Public Policies/" or not name.startswith("Public Policies/"):
            continue
        
        # Extract folder name (e.g., "Public Policies/AA/file.pdf" -> "AA")
        parts = name.replace("Public Policies/", "").split("/")
        if len(parts) >= 1:
            folder_name = parts[0]
            if folder_name and folder_name not in folders:
                folders[folder_name] = {"name": folder_name, "file_count": 0}
            if len(parts) >= 2 and parts[1].endswith(".pdf"):
                folders[folder_name]["file_count"] += 1
    
    return sorted(folders.values(), key=lambda x: x["name"])


def list_folder_files(folder_name: str) -> list[dict]:
    """
    List all PDF files in a specific folder from Supabase Storage.
    Returns list of {name, folder, path} dicts.
    """
    prefix = f"Public Policies/{folder_name}/"
    items = _list_storage_objects(prefix)
    
    files = []
    for item in items:
        name = item.get("name", "")
        if name.endswith(".pdf"):
            # Extract just the filename
            filename = name.split("/")[-1]
            files.append({
                "name": filename,
                "folder": folder_name,
                "path": name
            })
    
    return sorted(files, key=lambda x: x["name"])
