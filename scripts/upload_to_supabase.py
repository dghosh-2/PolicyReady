#!/usr/bin/env python3
"""
Upload PDFs and index.json to Supabase Storage.
Run this script once to populate the storage bucket.

Usage:
    cd PolicyReady
    source backend/venv/bin/activate
    python scripts/upload_to_supabase.py
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
BUCKET_NAME = "policyready"

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY/SUPABASE_ANON_KEY")
    print("Create a .env file with these variables:")
    print("  SUPABASE_URL=https://xxxxx.supabase.co")
    print("  SUPABASE_SERVICE_ROLE_KEY=eyJ...")
    sys.exit(1)

# Import supabase after checking env vars
from supabase import create_client

client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
POLICIES_DIR = PROJECT_ROOT / "Public Policies"
INDEX_FILE = PROJECT_ROOT / "backend" / "app" / "index_data" / "index.json"


def upload_file(local_path: Path, storage_path: str):
    """Upload a single file to Supabase Storage."""
    try:
        with open(local_path, "rb") as f:
            content = f.read()
        
        # Determine content type
        content_type = "application/pdf" if local_path.suffix == ".pdf" else "application/json"
        
        # Upload to storage
        result = client.storage.from_(BUCKET_NAME).upload(
            storage_path,
            content,
            {"content-type": content_type, "upsert": "true"}
        )
        return True
    except Exception as e:
        print(f"  ERROR uploading {storage_path}: {e}")
        return False


def main():
    print(f"Uploading to Supabase bucket: {BUCKET_NAME}")
    print(f"Project root: {PROJECT_ROOT}")
    print()
    
    # Upload index.json first
    if INDEX_FILE.exists():
        print("Uploading index.json...")
        if upload_file(INDEX_FILE, "index.json"):
            print(f"  ✓ index.json ({INDEX_FILE.stat().st_size / 1024 / 1024:.1f} MB)")
        else:
            print("  ✗ Failed to upload index.json")
    else:
        print(f"WARNING: Index file not found at {INDEX_FILE}")
        print("Run 'npm run index' first to build the index.")
    
    print()
    
    # Upload all PDFs
    if not POLICIES_DIR.exists():
        print(f"ERROR: Policies directory not found at {POLICIES_DIR}")
        sys.exit(1)
    
    pdf_files = list(POLICIES_DIR.rglob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF files to upload")
    print()
    
    uploaded = 0
    failed = 0
    
    for pdf_path in pdf_files:
        # Get relative path from POLICIES_DIR parent
        rel_path = pdf_path.relative_to(PROJECT_ROOT)
        storage_path = str(rel_path)
        
        print(f"Uploading: {rel_path}")
        if upload_file(pdf_path, storage_path):
            uploaded += 1
        else:
            failed += 1
    
    print()
    print(f"Upload complete!")
    print(f"  Uploaded: {uploaded}")
    print(f"  Failed: {failed}")
    
    if failed > 0:
        print()
        print("Some files failed to upload. You may need to:")
        print("1. Check your Supabase service role key has write permissions")
        print("2. Ensure the bucket exists and allows the file types")
        sys.exit(1)


if __name__ == "__main__":
    main()
