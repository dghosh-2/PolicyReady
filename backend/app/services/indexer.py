import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from .pdf_parser import extract_text_from_pdf, chunk_text, extract_keywords_from_text
from ..models import TextChunk, PolicyIndex


def build_index(policies_dir: str | Path, output_path: str | Path) -> PolicyIndex:
    """
    Build an inverted keyword index from all PDFs in the policies directory.
    
    Args:
        policies_dir: Path to the Public Policies folder
        output_path: Path to save the index JSON
        
    Returns:
        PolicyIndex with chunks and inverted index
    """
    policies_dir = Path(policies_dir)
    output_path = Path(output_path)
    
    chunks: list[TextChunk] = []
    inverted_index: dict[str, list[str]] = defaultdict(list)
    
    # Find all PDF files
    pdf_files = list(policies_dir.rglob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF files to index")
    
    chunk_id = 0
    for pdf_path in pdf_files:
        folder = pdf_path.parent.name
        filename = pdf_path.name
        
        try:
            pages = extract_text_from_pdf(pdf_path)
            
            for page_data in pages:
                page_num = page_data["page"]
                text = page_data["text"]
                
                # Split into chunks
                text_chunks = chunk_text(text, chunk_size=1500, overlap=300)
                
                for chunk_text_content in text_chunks:
                    # Extract keywords
                    keywords = extract_keywords_from_text(chunk_text_content)
                    
                    chunk = TextChunk(
                        id=f"{filename}_chunk_{chunk_id}",
                        source=filename,
                        folder=folder,
                        page=page_num,
                        text=chunk_text_content,
                        keywords=keywords
                    )
                    chunks.append(chunk)
                    
                    # Build inverted index
                    for keyword in keywords:
                        if chunk.id not in inverted_index[keyword]:
                            inverted_index[keyword].append(chunk.id)
                    
                    chunk_id += 1
                    
            print(f"  Indexed: {filename} ({len(pages)} pages)")
            
        except Exception as e:
            print(f"  Error indexing {filename}: {e}")
    
    # Create index object
    index = PolicyIndex(
        chunks=chunks,
        inverted_index=dict(inverted_index),
        metadata={
            "created_at": datetime.now().isoformat(),
            "total_chunks": str(len(chunks)),
            "total_keywords": str(len(inverted_index)),
            "source_dir": str(policies_dir)
        }
    )
    
    # Save to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(index.model_dump(), f, indent=2)
    
    print(f"\nIndex saved to {output_path}")
    print(f"Total chunks: {len(chunks)}")
    print(f"Total unique keywords: {len(inverted_index)}")
    
    return index


def load_index(index_path: str | Path) -> PolicyIndex:
    """
    Load a previously built index from JSON file.
    """
    index_path = Path(index_path)
    
    if not index_path.exists():
        raise FileNotFoundError(f"Index file not found: {index_path}")
    
    with open(index_path, 'r') as f:
        data = json.load(f)
    
    return PolicyIndex(**data)
