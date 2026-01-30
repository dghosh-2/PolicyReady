from pathlib import Path
from collections import defaultdict

from .indexer import load_index
from ..models import PolicyIndex, TextChunk, ChunkMatch


class KeywordSearchEngine:
    """
    Keyword-based search engine using an inverted index with fuzzy matching.
    """
    
    def __init__(self, index_path: str | Path | None = None, index_data: dict | None = None):
        self.index_path = Path(index_path) if index_path else None
        self._index: PolicyIndex | None = None
        self._chunk_map: dict[str, TextChunk] = {}
        self._index_data = index_data  # Pre-loaded index data (for Supabase)
    
    def load(self) -> None:
        """Load the index from disk or from pre-loaded data."""
        if self._index_data:
            # Load from pre-loaded data (Supabase)
            self._index = PolicyIndex(**self._index_data)
        elif self.index_path:
            # Load from local file
            self._index = load_index(self.index_path)
        else:
            raise ValueError("No index path or data provided")
        
        self._chunk_map = {chunk.id: chunk for chunk in self._index.chunks}
    
    @property
    def index(self) -> PolicyIndex:
        if self._index is None:
            self.load()
        return self._index
    
    def _find_matching_index_keywords(self, search_keyword: str) -> list[str]:
        """
        Find index keywords that match or contain the search keyword.
        Enables partial/fuzzy matching.
        """
        search_kw = search_keyword.lower()
        matches = []
        
        # Exact match
        if search_kw in self.index.inverted_index:
            matches.append(search_kw)
        
        # Partial matches - search keyword is contained in index keyword or vice versa
        for index_kw in self.index.inverted_index.keys():
            if index_kw == search_kw:
                continue
            # Check if one contains the other (for stemming-like behavior)
            if len(search_kw) >= 4 and len(index_kw) >= 4:
                if search_kw in index_kw or index_kw in search_kw:
                    matches.append(index_kw)
        
        return matches
    
    def search(self, keywords: list[str], top_k: int = 10) -> list[ChunkMatch]:
        """
        Search for chunks matching the given keywords with fuzzy matching.
        """
        if not keywords:
            return []
        
        # Normalize and expand keywords
        keywords = [kw.lower().strip() for kw in keywords if kw.strip()]
        
        # Score chunks
        chunk_scores: dict[str, float] = defaultdict(float)
        chunk_keyword_hits: dict[str, set] = defaultdict(set)
        
        for keyword in keywords:
            # Find all matching index keywords (exact + partial)
            matching_index_kws = self._find_matching_index_keywords(keyword)
            
            for index_kw in matching_index_kws:
                matching_chunk_ids = self.index.inverted_index[index_kw]
                # Exact match gets full score, partial gets 0.5
                score = 1.0 if index_kw == keyword else 0.5
                
                for chunk_id in matching_chunk_ids:
                    chunk_scores[chunk_id] += score
                    chunk_keyword_hits[chunk_id].add(keyword)
        
        if not chunk_scores:
            return []
        
        # Boost chunks that match more unique keywords
        for chunk_id in chunk_scores:
            unique_hits = len(chunk_keyword_hits[chunk_id])
            # Bonus for matching multiple different keywords
            chunk_scores[chunk_id] *= (1 + 0.2 * unique_hits)
        
        # Sort by score and get top_k
        sorted_chunks = sorted(
            chunk_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]
        
        # Build results
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
            "metadata": self.index.metadata
        }


# Global instance
_search_engine: KeywordSearchEngine | None = None


def get_search_engine() -> KeywordSearchEngine:
    """Get or create the global search engine instance."""
    global _search_engine
    if _search_engine is None:
        # Try Supabase first (for Vercel deployment)
        from .supabase_storage import is_supabase_configured, get_index_json
        
        if is_supabase_configured():
            print("Supabase configured, fetching index.json...")
            index_data = get_index_json()
            if index_data:
                print(f"Index loaded from Supabase: {len(index_data.get('chunks', []))} chunks")
                _search_engine = KeywordSearchEngine(index_data=index_data)
                _search_engine.load()
                return _search_engine
            else:
                print("Failed to fetch index.json from Supabase")
        
        # Fall back to local file (for local development)
        index_path = Path(__file__).parent.parent / "index_data" / "index.json"
        if not index_path.exists():
            raise FileNotFoundError(f"Index not found at {index_path}")
        print(f"Loading index from local file: {index_path}")
        _search_engine = KeywordSearchEngine(index_path=index_path)
        _search_engine.load()
    return _search_engine
