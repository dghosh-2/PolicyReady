"""
Supabase Storage service for fetching PDFs and index data.
Used in Vercel deployment where local filesystem is not available.
"""
import os
import json
import tempfile
from functools import lru_cache
from typing import Optional

# Only import supabase if available (for Vercel deployment)
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
BUCKET_NAME = "policyready"


def is_supabase_configured() -> bool:
    """Check if Supabase is configured for use."""
    return SUPABASE_AVAILABLE and bool(SUPABASE_URL) and bool(SUPABASE_KEY)


@lru_cache(maxsize=1)
def get_supabase_client() -> Optional[Client]:
    """Get or create Supabase client (cached)."""
    if not is_supabase_configured():
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def get_index_json() -> Optional[dict]:
    """
    Fetch index.json from Supabase Storage.
    Returns the parsed JSON data or None if not available.
    """
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        response = client.storage.from_(BUCKET_NAME).download("index.json")
        return json.loads(response)
    except Exception as e:
        print(f"Error fetching index.json from Supabase: {e}")
        return None


def download_pdf_to_temp(folder: str, filename: str) -> Optional[str]:
    """
    Download a PDF from Supabase Storage to a temporary file.
    Returns the path to the temp file, or None if failed.
    """
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        # Path in storage: Public Policies/AA/filename.pdf
        storage_path = f"Public Policies/{folder}/{filename}"
        response = client.storage.from_(BUCKET_NAME).download(storage_path)
        
        # Write to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp.write(response)
            return tmp.name
    except Exception as e:
        print(f"Error downloading PDF from Supabase: {e}")
        return None


def list_policy_folders() -> list[dict]:
    """
    List all policy folders and their file counts from Supabase Storage.
    Returns list of {name, file_count} dicts.
    """
    client = get_supabase_client()
    if not client:
        return []
    
    try:
        # List folders in Public Policies/
        response = client.storage.from_(BUCKET_NAME).list("Public Policies")
        folders = []
        
        for item in response:
            if item.get("id") is None:  # It's a folder
                folder_name = item["name"]
                # Count files in this folder
                files = client.storage.from_(BUCKET_NAME).list(f"Public Policies/{folder_name}")
                pdf_count = sum(1 for f in files if f.get("name", "").endswith(".pdf"))
                folders.append({"name": folder_name, "file_count": pdf_count})
        
        return sorted(folders, key=lambda x: x["name"])
    except Exception as e:
        print(f"Error listing folders from Supabase: {e}")
        return []


def list_folder_files(folder_name: str) -> list[dict]:
    """
    List all PDF files in a specific folder from Supabase Storage.
    Returns list of {name, folder, path} dicts.
    """
    client = get_supabase_client()
    if not client:
        return []
    
    try:
        response = client.storage.from_(BUCKET_NAME).list(f"Public Policies/{folder_name}")
        files = []
        
        for item in response:
            name = item.get("name", "")
            if name.endswith(".pdf"):
                files.append({
                    "name": name,
                    "folder": folder_name,
                    "path": f"Public Policies/{folder_name}/{name}"
                })
        
        return sorted(files, key=lambda x: x["name"])
    except Exception as e:
        print(f"Error listing files from Supabase: {e}")
        return []
