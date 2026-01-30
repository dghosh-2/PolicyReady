import os
import asyncio
from typing import Optional, AsyncGenerator
from pydantic import BaseModel, Field
from openai import AsyncOpenAI, RateLimitError, APITimeoutError
from dotenv import load_dotenv

from ..models import (
    ComplianceStatus,
    ComplianceAnswer,
    ChunkMatch
)

load_dotenv()

client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=30.0  # 30 second timeout
)

# Higher concurrency for speed
MAX_CONCURRENT = 10
semaphore = asyncio.Semaphore(MAX_CONCURRENT)


class KeywordsResult(BaseModel):
    keywords: list[str]


class AnswerResult(BaseModel):
    status: str = Field(description="MET, NOT_MET, or PARTIAL")
    quote: Optional[str] = Field(default=None, description="Exact quote from document")
    doc: Optional[str] = Field(default=None, description="Document name")
    page: Optional[int] = Field(default=None)


async def _call_with_retry(coro, max_retries=2):
    """Retry with backoff on rate limit or timeout."""
    for attempt in range(max_retries):
        try:
            async with semaphore:
                return await coro
        except (RateLimitError, APITimeoutError) as e:
            if attempt == max_retries - 1:
                print(f"API error after {max_retries} attempts: {e}")
                return None
            await asyncio.sleep((attempt + 1) * 2)
    return None


async def extract_keywords_single(question: str, idx: int) -> tuple[int, list[str]]:
    """Extract keywords for a single question."""
    
    response = await _call_with_retry(
        client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Return JSON with keywords array. 5-8 search terms."},
                {"role": "user", "content": question}
            ],
            response_format=KeywordsResult,
            temperature=0,
            max_tokens=100
        )
    )
    
    if response and response.choices[0].message.parsed:
        return (idx, response.choices[0].message.parsed.keywords)
    return (idx, [])


async def extract_all_keywords_parallel(questions: list[str]) -> list[list[str]]:
    """Extract keywords for all questions in parallel."""
    
    tasks = [extract_keywords_single(q, idx) for idx, q in enumerate(questions)]
    results = await asyncio.gather(*tasks)
    results.sort(key=lambda x: x[0])
    return [kw for _, kw in results]


async def answer_single_question(
    idx: int,
    question: str,
    evidence_chunks: list[ChunkMatch]
) -> tuple[int, ComplianceAnswer]:
    """Answer a single compliance question."""
    
    # Minimal evidence - just top 2 chunks, truncated
    evidence = ""
    if evidence_chunks:
        for c in evidence_chunks[:2]:
            text = c.text[:600]
            evidence += f"[{c.source} p{c.page}] {text}\n"
    
    if not evidence:
        # No evidence found - return NOT_MET immediately without API call
        return (idx, ComplianceAnswer(
            question=question,
            status=ComplianceStatus.NOT_MET,
            evidence=None,
            source=None,
            page=None,
            confidence=0.0,
            reasoning="No relevant policy documents found"
        ))
    
    prompt = f"Q:{question}\nDocs:\n{evidence}"
    
    response = await _call_with_retry(
        client.beta.chat.completions.parse(
            model="gpt-4o-mini",  # Fast model
            messages=[
                {"role": "system", "content": "MET=quote proves requirement. NOT_MET=no proof. PARTIAL=incomplete. Return exact quote if MET/PARTIAL."},
                {"role": "user", "content": prompt}
            ],
            response_format=AnswerResult,
            temperature=0,
            max_tokens=300
        )
    )
    
    if response and response.choices[0].message.parsed:
        r = response.choices[0].message.parsed
        status = ComplianceStatus.NOT_MET
        if r.status.upper() == "MET":
            status = ComplianceStatus.MET
        elif r.status.upper() == "PARTIAL":
            status = ComplianceStatus.PARTIAL
        
        return (idx, ComplianceAnswer(
            question=question,
            status=status,
            evidence=r.quote,
            source=r.doc,
            page=r.page,
            confidence=0.8 if status == ComplianceStatus.MET else 0.5,
            reasoning=""  # No reasoning - just evidence
        ))
    
    # API failed - return NOT_MET
    return (idx, ComplianceAnswer(
        question=question,
        status=ComplianceStatus.NOT_MET,
        evidence=None,
        source=None,
        page=None,
        confidence=0.0,
        reasoning=""
    ))


async def answer_all_questions_streaming(
    questions: list[str],
    evidence_per_question: list[list[ChunkMatch]]
) -> AsyncGenerator[tuple[int, ComplianceAnswer], None]:
    """Answer all questions in parallel, yielding results as they complete."""
    
    tasks = [
        asyncio.create_task(answer_single_question(idx, q, evidence))
        for idx, (q, evidence) in enumerate(zip(questions, evidence_per_question))
    ]
    
    for coro in asyncio.as_completed(tasks):
        result = await coro
        yield result
