import gzip
import json
import sqlite3
import pickle
import time
from pathlib import Path
from collections import defaultdict
from contextlib import contextmanager
from typing import Optional

from .indexer import load_index
from ..models import PolicyIndex, TextChunk, ChunkMatch


class KeywordSearchEngine:
    """
    Keyword-based search engine using an inverted index with fuzzy matching.
    Supports both JSON and SQLite backends for flexibility.
    """
    
    def __init__(self, index_path: str | Path | None = None, index_data: dict | None = None):
        self.index_path = Path(index_path) if index_path else None
        self._index: PolicyIndex | None = None
        self._chunk_map: dict[str, TextChunk] = {}
        self._index_data = index_data
        self._loaded = False
        self._load_time: float = 0
    
    def load(self) -> None:
        """Load the index from disk or from pre-loaded data."""
        if self._loaded:
            return
            
        start = time.time()
        
        if self._index_data:
            self._index = PolicyIndex(**self._index_data)
        elif self.index_path:
            self._index = load_index(self.index_path)
        else:
            raise ValueError("No index path or data provided")
        
        self._chunk_map = {chunk.id: chunk for chunk in self._index.chunks}
        self._loaded = True
        self._load_time = time.time() - start
        print(f"Index loaded in {self._load_time:.2f}s: {len(self._chunk_map)} chunks, {len(self._index.inverted_index)} keywords")
    
    @property
    def is_loaded(self) -> bool:
        return self._loaded
    
    @property
    def index(self) -> PolicyIndex:
        if self._index is None:
            self.load()
        return self._index
    
    def _find_matching_index_keywords(self, search_keyword: str) -> list[str]:
        """Find index keywords that match or contain the search keyword."""
        search_kw = search_keyword.lower()
        matches = []
        
        if search_kw in self.index.inverted_index:
            matches.append(search_kw)
        
        for index_kw in self.index.inverted_index.keys():
            if index_kw == search_kw:
                continue
            if len(search_kw) >= 4 and len(index_kw) >= 4:
                if search_kw in index_kw or index_kw in search_kw:
                    matches.append(index_kw)
        
        return matches
    
    def search(self, keywords: list[str], top_k: int = 10) -> list[ChunkMatch]:
        """Search for chunks matching the given keywords."""
        if not keywords:
            return []
        
        keywords = [kw.lower().strip() for kw in keywords if kw.strip()]
        
        chunk_scores: dict[str, float] = defaultdict(float)
        chunk_keyword_hits: dict[str, set] = defaultdict(set)
        
        for keyword in keywords:
            matching_index_kws = self._find_matching_index_keywords(keyword)
            
            for index_kw in matching_index_kws:
                matching_chunk_ids = self.index.inverted_index[index_kw]
                score = 1.0 if index_kw == keyword else 0.5
                
                for chunk_id in matching_chunk_ids:
                    chunk_scores[chunk_id] += score
                    chunk_keyword_hits[chunk_id].add(keyword)
        
        if not chunk_scores:
            return []
        
        for chunk_id in chunk_scores:
            unique_hits = len(chunk_keyword_hits[chunk_id])
            chunk_scores[chunk_id] *= (1 + 0.2 * unique_hits)
        
        sorted_chunks = sorted(
            chunk_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]
        
        results = []
        for chunk_id, score in sorted_chunks:
            chunk = self._chunk_map.get(chunk_id)
            if chunk:
                results.append(ChunkMatch(
                    chunk_id=chunk_id,
                    source=chunk.source,
                    page=chunk.page,
                    text=chunk.text,
                    score=score
                ))
        
        return results
    
    def search_batch(
        self, 
        keyword_sets: list[list[str]], 
        top_k_per_query: int = 5
    ) -> list[list[ChunkMatch]]:
        """Search for multiple keyword sets at once."""
        return [
            self.search(keywords, top_k=top_k_per_query)
            for keywords in keyword_sets
        ]
    
    def get_stats(self) -> dict:
        """Get statistics about the loaded index."""
        return {
            "total_chunks": len(self.index.chunks),
            "total_keywords": len(self.index.inverted_index),
            "metadata": self.index.metadata,
            "load_time_seconds": self._load_time
        }


# Global instance - lazy loaded
_search_engine: Optional[KeywordSearchEngine] = None
_index_loading = False
_index_load_error: Optional[str] = None


def _load_index_data() -> dict:
    """Load index data from the best available source."""
    from .supabase_storage import is_supabase_configured, get_index_json
    
    # Try Supabase first
    if is_supabase_configured():
        print("Supabase configured, fetching index...")
        index_data = get_index_json()
        if index_data:
            print(f"Index loaded from Supabase: {len(index_data.get('chunks', []))} chunks")
            return index_data
        print("Failed to fetch from Supabase, falling back to local")
    
    # Fall back to local file
    index_dir = Path(__file__).parent.parent / "index_data"
    index_gz_path = index_dir / "index.json.gz"
    index_path = index_dir / "index.json"
    
    if index_gz_path.exists():
        print(f"Loading index from gzipped file: {index_gz_path}")
        start = time.time()
        with gzip.open(index_gz_path, 'rt', encoding='utf-8') as f:
            data = json.load(f)
        print(f"JSON parsed in {time.time() - start:.2f}s")
        return data
    elif index_path.exists():
        print(f"Loading index from JSON file: {index_path}")
        with open(index_path, 'r') as f:
            return json.load(f)
    else:
        raise FileNotFoundError(f"Index not found at {index_path} or {index_gz_path}")


def preload_index() -> bool:
    """
    Preload the index at startup. Call this from FastAPI startup event.
    Returns True if successful, False otherwise.
    """
    global _search_engine, _index_loading, _index_load_error
    
    if _search_engine is not None and _search_engine.is_loaded:
        return True
    
    if _index_loading:
        return False
    
    _index_loading = True
    try:
        print("Preloading search index at startup...")
        start = time.time()
        index_data = _load_index_data()
        _search_engine = KeywordSearchEngine(index_data=index_data)
        _search_engine.load()
        print(f"Index preloaded successfully in {time.time() - start:.2f}s total")
        _index_load_error = None
        return True
    except Exception as e:
        _index_load_error = str(e)
        print(f"Failed to preload index: {e}")
        return False
    finally:
        _index_loading = False


def get_search_engine() -> KeywordSearchEngine:
    """Get the search engine, loading it if necessary."""
    global _search_engine
    
    if _search_engine is None or not _search_engine.is_loaded:
        # Lazy load if not preloaded
        preload_index()
    
    if _search_engine is None:
        raise FileNotFoundError(_index_load_error or "Index not loaded")
    
    return _search_engine


def is_index_loaded() -> bool:
    """Check if the index is loaded without triggering a load."""
    return _search_engine is not None and _search_engine.is_loaded


def get_index_status() -> dict:
    """Get index loading status without triggering a load."""
    return {
        "loaded": is_index_loaded(),
        "loading": _index_loading,
        "error": _index_load_error
    }
