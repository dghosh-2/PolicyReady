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

# Reduced batch size for better accuracy (was 5)
MAX_CONCURRENT = 5
BATCH_SIZE = 3  # Process 3 questions per API call for better focus

# Healthcare domain synonyms for better search coverage
HEALTHCARE_SYNONYMS = {
    # Member/Patient terms
    "member": ["patient", "enrollee", "beneficiary", "subscriber", "participant", "individual"],
    "patient": ["member", "enrollee", "beneficiary", "individual"],
    "enrollee": ["member", "patient", "beneficiary", "subscriber"],
    
    # Provider terms
    "provider": ["physician", "doctor", "practitioner", "clinician", "specialist", "healthcare provider"],
    "physician": ["provider", "doctor", "practitioner", "clinician"],
    "doctor": ["provider", "physician", "practitioner", "clinician"],
    
    # Grievance/Complaint terms
    "grievance": ["complaint", "appeal", "dispute", "concern", "issue", "problem", "grievances"],
    "complaint": ["grievance", "appeal", "dispute", "concern", "issue", "complaints"],
    "appeal": ["grievance", "complaint", "dispute", "review", "reconsideration", "appeals"],
    "appeals": ["appeal", "grievance", "complaint", "dispute", "review", "reconsideration"],
    
    # Credentialing terms
    "credentialing": ["credentialed", "credentials", "privileging", "verification", "qualification"],
    "credentials": ["credentialing", "privileging", "qualifications", "certification"],
    
    # Authorization terms
    "authorization": ["approval", "preauthorization", "prior authorization", "pre-approval", "certified"],
    "preauthorization": ["authorization", "prior authorization", "pre-approval", "precertification"],
    "approval": ["authorization", "approved", "certified", "granted"],
    
    # Coverage terms
    "coverage": ["benefit", "covered", "benefits", "plan", "insurance"],
    "benefit": ["coverage", "covered", "benefits", "entitlement"],
    "benefits": ["coverage", "benefit", "covered services", "entitlements"],
    
    # Care management terms
    "care": ["treatment", "service", "services", "healthcare", "medical care"],
    "treatment": ["care", "therapy", "service", "intervention", "procedure"],
    "service": ["care", "treatment", "services", "procedure"],
    
    # Quality terms
    "quality": ["performance", "standards", "metrics", "outcomes", "measures"],
    "compliance": ["adherence", "conformance", "regulatory", "requirements"],
    
    # Network terms
    "network": ["contracted", "participating", "in-network", "panel"],
    "contracted": ["network", "participating", "agreement"],
    
    # Utilization terms
    "utilization": ["use", "usage", "review", "management", "um"],
    "review": ["evaluation", "assessment", "analysis", "audit"],
    
    # Access terms
    "access": ["availability", "accessible", "timely", "appointment"],
    "timely": ["prompt", "within", "timeframe", "deadline", "days"],
    
    # Documentation terms
    "documentation": ["records", "documents", "documented", "paperwork", "files"],
    "policy": ["policies", "procedure", "guideline", "protocol", "rule"],
    "procedure": ["process", "policy", "protocol", "guideline", "method"],
    
    # Notification terms
    "notification": ["notice", "notify", "inform", "communication", "letter"],
    "notice": ["notification", "notify", "inform", "communication"],
    
    # Rights terms
    "rights": ["right", "entitlement", "entitled", "protection"],
    
    # Denial terms
    "denial": ["denied", "deny", "rejection", "adverse", "unfavorable"],
    "denied": ["denial", "deny", "rejected", "adverse"],
    
    # Emergency terms
    "emergency": ["urgent", "emergent", "crisis", "immediate"],
    "urgent": ["emergency", "emergent", "immediate", "priority"],
    
    # Behavioral health terms
    "behavioral": ["mental", "psychiatric", "psychological", "behavioral health"],
    "mental": ["behavioral", "psychiatric", "psychological", "mental health"],
    
    # Pharmacy terms
    "pharmacy": ["prescription", "drug", "medication", "formulary", "pharmaceutical"],
    "prescription": ["pharmacy", "drug", "medication", "rx"],
    "medication": ["drug", "prescription", "medicine", "pharmaceutical"],
    
    # HIPAA/Privacy terms
    "hipaa": ["privacy", "confidentiality", "protected health information", "phi"],
    "privacy": ["hipaa", "confidentiality", "confidential", "protected"],
    "confidentiality": ["privacy", "confidential", "hipaa", "protected"],
}


def expand_keywords_with_synonyms(keywords: list[str]) -> list[str]:
    """Expand keywords with healthcare domain synonyms."""
    expanded = set(keywords)
    
    for keyword in keywords:
        kw_lower = keyword.lower()
        # Check if this keyword has synonyms
        if kw_lower in HEALTHCARE_SYNONYMS:
            for synonym in HEALTHCARE_SYNONYMS[kw_lower]:
                expanded.add(synonym.lower())
        
        # Also check if any synonym maps back to this keyword
        for base_term, synonyms in HEALTHCARE_SYNONYMS.items():
            if kw_lower in [s.lower() for s in synonyms]:
                expanded.add(base_term)
                for syn in synonyms:
                    expanded.add(syn.lower())
    
    return list(expanded)


def extract_keywords_local(question: str) -> list[str]:
    """
    Extract keywords from a question using local NLP with synonym expansion.
    """
    # Get base keywords
    keywords = extract_keywords_from_text(question)
    
    # Expand with healthcare synonyms
    expanded = expand_keywords_with_synonyms(keywords)
    
    # Return expanded keywords (more terms = better search coverage)
    return expanded[:15]  # Increased from 8 to 15 for better coverage


def extract_all_keywords_local(questions: list[str]) -> list[list[str]]:
    """Extract keywords for all questions locally with synonym expansion."""
    return [extract_keywords_local(q) for q in questions]


async def extract_all_keywords_parallel(questions: list[str]) -> list[list[str]]:
    """Extract keywords for all questions - uses local NLP with synonym expansion."""
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
            # Build evidence string - use top 3 chunks for better coverage (was 2)
            evidence_str = ""
            for c in evidence_chunks[:3]:
                text = c.text[:600]  # Slightly more text per chunk
                evidence_str += f"[{c.source} p{c.page}] {text}\n"
            questions_with_evidence.append((idx, question, evidence_str))
    
    # If no questions need API analysis, return early
    if not questions_with_evidence:
        return no_evidence_results
    
    # Improved system prompt for better accuracy
    system_prompt = """You are an expert healthcare compliance analyst reviewing policy documents.

For each question, carefully analyze the provided evidence and determine:
- MET: The evidence CLEARLY and DIRECTLY addresses the requirement. There is explicit policy language that satisfies the question.
- PARTIAL: The evidence partially addresses the requirement but is incomplete, vague, or only indirectly related.
- NOT_MET: The evidence does not address the requirement, or no relevant evidence was found.

IMPORTANT: Be thorough in your analysis. If the evidence contains relevant policy language that addresses the question's requirement, mark it as MET. Look for:
- Direct statements of policy or procedure
- Requirements, standards, or guidelines that address the question
- Processes or protocols that fulfill the requirement

Respond with valid JSON:
{
  "answers": [
    {"index": 0, "status": "MET", "quote": "exact quote proving compliance", "doc": "filename", "page": 1},
    {"index": 1, "status": "NOT_MET", "quote": null, "doc": null, "page": null}
  ]
}

Rules:
- Analyze each question INDEPENDENTLY and thoroughly
- Include the exact quote from the evidence for MET or PARTIAL
- Use the question index number (from Q0, Q1, etc.) for the "index" field
- Be generous in marking MET if evidence clearly supports the requirement"""

    user_prompt = _build_batch_prompt(questions_with_evidence)
    
    # Use JSON mode
    response = await _call_with_retry(
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=2000  # Increased for more detailed responses
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
                    # Try direct index mapping
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
                    confidence=0.85 if status == ComplianceStatus.MET else 0.6,
                    reasoning=""
                )))
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
    
    # Check if we got results for all questions with evidence
    result_indices = {idx for idx, _ in results}
    for idx, question, _ in questions_with_evidence:
        if idx not in result_indices:
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
