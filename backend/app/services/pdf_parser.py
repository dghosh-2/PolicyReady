import re
from pathlib import Path
import pymupdf


def extract_text_from_pdf(pdf_path: str | Path) -> list[dict]:
    """
    Extract text from a PDF file, returning a list of page contents.
    Each item contains page number and text content.
    """
    pdf_path = Path(pdf_path)
    pages = []
    
    try:
        doc = pymupdf.open(str(pdf_path))
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text")
            if text.strip():
                pages.append({
                    "page": page_num,
                    "text": text.strip()
                })
        doc.close()
    except Exception as e:
        raise RuntimeError(f"Failed to parse PDF {pdf_path}: {e}")
    
    return pages


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """
    Split text into overlapping chunks for better context preservation.
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind(". ")
            if last_period > chunk_size // 2:
                chunk = chunk[:last_period + 1]
                end = start + last_period + 1
        
        chunks.append(chunk.strip())
        start = end - overlap
        
        if start >= len(text):
            break
    
    return chunks


def extract_questions_from_pdf(pdf_path: str | Path) -> list[str]:
    """
    Extract questions from an audit PDF.
    Uses regex to find sentences ending with '?'.
    """
    pages = extract_text_from_pdf(pdf_path)
    full_text = "\n".join(page["text"] for page in pages)
    
    # Clean up the text
    full_text = re.sub(r'\s+', ' ', full_text)
    
    # Find all sentences ending with ?
    # Match text that ends with ? and has reasonable length
    question_pattern = r'[^.!?\n]*\?'
    matches = re.findall(question_pattern, full_text)
    
    questions = []
    for match in matches:
        question = match.strip()
        # Filter out very short matches (likely not real questions)
        if len(question) > 20:
            questions.append(question)
    
    return questions


def extract_keywords_from_text(text: str) -> list[str]:
    """
    Extract keywords from text using simple tokenization.
    Removes common stop words and short words.
    """
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
        'that', 'this', 'these', 'those', 'it', 'its', 'they', 'them', 'their',
        'he', 'she', 'his', 'her', 'we', 'our', 'you', 'your', 'who', 'which',
        'what', 'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both',
        'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
        'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just', 'also',
        'any', 'if', 'then', 'else', 'about', 'into', 'through', 'during',
        'before', 'after', 'above', 'below', 'between', 'under', 'again',
        'further', 'once', 'here', 'there', 'because', 'while', 'although'
    }
    
    # Tokenize: split on non-alphanumeric characters
    words = re.findall(r'\b[a-zA-Z0-9]+\b', text.lower())
    
    # Filter stop words and short words
    keywords = [
        word for word in words 
        if word not in stop_words and len(word) > 2
    ]
    
    # Remove duplicates while preserving order
    seen = set()
    unique_keywords = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)
    
    return unique_keywords
