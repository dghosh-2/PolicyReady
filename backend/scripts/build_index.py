#!/usr/bin/env python3
"""
Script to build the keyword index from all policy PDFs.
Run this once before starting the application.

Usage:
    cd backend
    python scripts/build_index.py
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.indexer import build_index


def main():
    # Paths relative to project root
    project_root = Path(__file__).parent.parent.parent
    policies_dir = project_root / "Public Policies"
    output_path = Path(__file__).parent.parent / "app" / "index_data" / "index.json"
    
    if not policies_dir.exists():
        print(f"Error: Policies directory not found: {policies_dir}")
        sys.exit(1)
    
    print(f"Building index from: {policies_dir}")
    print(f"Output will be saved to: {output_path}")
    print("-" * 50)
    
    index = build_index(policies_dir, output_path)
    
    print("-" * 50)
    print("Index build complete!")
    print(f"  - Total chunks indexed: {len(index.chunks)}")
    print(f"  - Total unique keywords: {len(index.inverted_index)}")


if __name__ == "__main__":
    main()
