import os
import asyncio
import json
from typing import Optional, AsyncGenerator
from openai import AsyncOpenAI, RateLimitError, APITimeoutError
from dotenv import load_dotenv

from ..models import (
    ComplianceStatus,
    ComplianceAnswer,
    ChunkMatch
)
from .pdf_parser import extract_keywords_from_text

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("WARNING: OPENAI_API_KEY not set!")

client = AsyncOpenAI(
    api_key=OPENAI_API_KEY,
    timeout=30.0
)

# Higher concurrency for batched requests
MAX_CONCURRENT = 5
BATCH_SIZE = 5  # Process 5 questions per API call


def extract_keywords_local(question: str) -> list[str]:
    """
    Extract keywords from a question using local NLP (no API call).
    Uses the existing extract_keywords_from_text function.
    """
    keywords = extract_keywords_from_text(question)
    # Return top 8 keywords (most relevant for search)
    return keywords[:8]


def extract_all_keywords_local(questions: list[str]) -> list[list[str]]:
    """Extract keywords for all questions locally (instant, no API calls)."""
    return [extract_keywords_local(q) for q in questions]


# Keep the async version for API compatibility but use local extraction
async def extract_all_keywords_parallel(questions: list[str]) -> list[list[str]]:
    """Extract keywords for all questions - now uses local NLP instead of LLM."""
    # This is now instant - no API calls needed!
    return extract_all_keywords_local(questions)


async def _call_with_retry(coro, semaphore: asyncio.Semaphore, max_retries=2):
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


def _build_batch_prompt(questions_with_evidence: list[tuple[int, str, str]]) -> str:
    """Build a prompt for analyzing multiple questions at once."""
    prompt_parts = []
    for idx, question, evidence in questions_with_evidence:
        prompt_parts.append(f"[Q{idx}] {question}\nEvidence:\n{evidence}\n")
    return "\n---\n".join(prompt_parts)


async def _answer_batch(
    batch: list[tuple[int, str, list[ChunkMatch]]],
    semaphore: asyncio.Semaphore
) -> list[tuple[int, ComplianceAnswer]]:
    """Answer a batch of questions in a single API call using JSON mode."""
    
    # Separate questions with and without evidence
    questions_with_evidence = []
    no_evidence_results = []
    
    for idx, question, evidence_chunks in batch:
        if not evidence_chunks:
            # No evidence - return NOT_MET immediately without API call
            no_evidence_results.append((idx, ComplianceAnswer(
                question=question,
                status=ComplianceStatus.NOT_MET,
                evidence=None,
                source=None,
                page=None,
                confidence=0.0,
                reasoning="No relevant policy documents found"
            )))
        else:
            # Build evidence string (top 2 chunks, truncated)
            evidence_str = ""
            for c in evidence_chunks[:2]:
                text = c.text[:500]
                evidence_str += f"[{c.source} p{c.page}] {text}\n"
            questions_with_evidence.append((idx, question, evidence_str))
    
    # If no questions need API analysis, return early
    if not questions_with_evidence:
        return no_evidence_results
    
    # Build batch prompt with explicit JSON format instructions
    system_prompt = """You are a compliance analyst. Analyze each question against its evidence.

For each question, determine:
- MET: Evidence clearly proves the requirement is met
- NOT_MET: No evidence proves the requirement  
- PARTIAL: Evidence is incomplete or unclear

You MUST respond with valid JSON in this exact format:
{
  "answers": [
    {"index": 0, "status": "MET", "quote": "exact quote from doc", "doc": "filename", "page": 1},
    {"index": 1, "status": "NOT_MET", "quote": null, "doc": null, "page": null}
  ]
}

Rules:
- Include exact quotes only for MET or PARTIAL status
- Use the question index (Q0, Q1, etc.) for the "index" field
- status must be exactly "MET", "NOT_MET", or "PARTIAL"
- Return one answer object per question"""

    user_prompt = _build_batch_prompt(questions_with_evidence)
    
    # Use JSON mode instead of structured outputs to avoid schema issues
    response = await _call_with_retry(
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=1500
        ),
        semaphore
    )
    
    results = list(no_evidence_results)
    
    if response and response.choices[0].message.content:
        try:
            parsed = json.loads(response.choices[0].message.content)
            answers_list = parsed.get("answers", [])
            
            # Map results back to original indices
            idx_to_question = {idx: q for idx, q, _ in questions_with_evidence}
            
            for answer in answers_list:
                orig_idx = answer.get("index")
                if orig_idx is None:
                    continue
                
                # Find the actual question index from our batch
                actual_idx = None
                for batch_idx, question, _ in questions_with_evidence:
                    if batch_idx == orig_idx:
                        actual_idx = batch_idx
                        break
                
                if actual_idx is None:
                    # Try direct index mapping (in case model returned 0, 1, 2 instead of actual indices)
                    if isinstance(orig_idx, int) and orig_idx < len(questions_with_evidence):
                        actual_idx = questions_with_evidence[orig_idx][0]
                    else:
                        continue
                
                question = idx_to_question.get(actual_idx, "")
                
                status_str = str(answer.get("status", "NOT_MET")).upper()
                status = ComplianceStatus.NOT_MET
                if status_str == "MET":
                    status = ComplianceStatus.MET
                elif status_str == "PARTIAL":
                    status = ComplianceStatus.PARTIAL
                
                results.append((actual_idx, ComplianceAnswer(
                    question=question,
                    status=status,
                    evidence=answer.get("quote"),
                    source=answer.get("doc"),
                    page=answer.get("page"),
                    confidence=0.8 if status == ComplianceStatus.MET else 0.5,
                    reasoning=""
                )))
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            # Fall through to error handling below
    
    # Check if we got results for all questions with evidence
    result_indices = {idx for idx, _ in results}
    for idx, question, _ in questions_with_evidence:
        if idx not in result_indices:
            # API failed for this question - return NOT_MET
            results.append((idx, ComplianceAnswer(
                question=question,
                status=ComplianceStatus.NOT_MET,
                evidence=None,
                source=None,
                page=None,
                confidence=0.0,
                reasoning="Analysis failed"
            )))
    
    return results


async def answer_all_questions_streaming(
    questions: list[str],
    evidence_per_question: list[list[ChunkMatch]]
) -> AsyncGenerator[tuple[int, ComplianceAnswer], None]:
    """Answer all questions in batches, yielding results as they complete."""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    
    # Create batches of questions
    all_items = list(enumerate(zip(questions, evidence_per_question)))
    batches = []
    
    for i in range(0, len(all_items), BATCH_SIZE):
        batch = [(idx, q, ev) for idx, (q, ev) in all_items[i:i + BATCH_SIZE]]
        batches.append(batch)
    
    print(f"Processing {len(questions)} questions in {len(batches)} batches of up to {BATCH_SIZE}")
    
    # Process batches in parallel
    tasks = [
        asyncio.create_task(_answer_batch(batch, semaphore))
        for batch in batches
    ]
    
    # Yield results as batches complete
    for coro in asyncio.as_completed(tasks):
        batch_results = await coro
        for result in batch_results:
            yield result
