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
    """Build Supabase Storage API URL for downloading objects."""
    # Use /public/ for public buckets, /authenticated/ for private
    base = f"{SUPABASE_URL}/storage/v1/object/public"
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
    """
    List objects in Supabase Storage with given prefix.
    Uses the POST /storage/v1/object/list/{bucket} endpoint.
    """
    if not is_supabase_configured():
        return []
    
    try:
        url = f"{SUPABASE_URL}/storage/v1/object/list/{BUCKET_NAME}"
        
        # The API expects prefix without trailing slash for folder listing
        # and returns objects within that prefix
        clean_prefix = prefix.rstrip("/")
        
        response = httpx.post(
            url,
            headers={
                **_get_headers(),
                "Content-Type": "application/json"
            },
            json={
                "prefix": clean_prefix,
                "limit": 1000,
                "offset": 0,
                "sortBy": {
                    "column": "name",
                    "order": "asc"
                }
            },
            timeout=30.0
        )
        response.raise_for_status()
        result = response.json()
        print(f"Storage list response for prefix '{clean_prefix}': {len(result)} items")
        return result
    except Exception as e:
        print(f"Error listing objects from Supabase: {e}")
        import traceback
        traceback.print_exc()
        return []


def list_policy_folders() -> list[dict]:
    """
    List all policy folders and their file counts from Supabase Storage.
    Returns list of {name, file_count} dicts.
    """
    # List the "Public Policies" directory to get folders
    items = _list_storage_objects("Public Policies")
    
    folders = []
    for item in items:
        name = item.get("name", "")
        # Skip files at root level, only get folders (folders have id = null typically)
        # In Supabase storage, folders appear as items with metadata
        item_id = item.get("id")
        
        # If it's a folder (no id or has metadata indicating folder)
        # We need to count files in each folder
        if name and not name.endswith(".pdf") and not name.endswith(".json"):
            # This is likely a folder, count its contents
            folder_items = _list_storage_objects(f"Public Policies/{name}")
            pdf_count = sum(1 for f in folder_items if f.get("name", "").endswith(".pdf"))
            folders.append({"name": name, "file_count": pdf_count})
    
    return sorted(folders, key=lambda x: x["name"])


def list_folder_files(folder_name: str) -> list[dict]:
    """
    List all PDF files in a specific folder from Supabase Storage.
    Returns list of {name, folder, path} dicts.
    """
    prefix = f"Public Policies/{folder_name}"
    items = _list_storage_objects(prefix)
    
    files = []
    for item in items:
        name = item.get("name", "")
        if name.endswith(".pdf"):
            files.append({
                "name": name,
                "folder": folder_name,
                "path": f"Public Policies/{folder_name}/{name}"
            })
    
    return sorted(files, key=lambda x: x["name"])
