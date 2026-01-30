import os
import json
import tempfile
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

from .models import (
    PoliciesResponse,
    PolicyFolder,
    PolicyFile,
    FolderContentsResponse,
    AnalysisResponse,
    ComplianceStatus
)
from .services.pdf_parser import extract_questions_from_pdf, extract_text_from_pdf
from .services.search import get_search_engine
from .services.llm import extract_all_keywords_parallel, answer_all_questions_streaming
from .services.supabase_storage import (
    is_supabase_configured,
    list_policy_folders,
    list_folder_files,
    download_pdf_to_temp
)

load_dotenv()

app = FastAPI(title="PolicyReady API", version="1.0.0")

# Allow all origins for Vercel deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

POLICIES_DIR = Path(__file__).parent.parent.parent / "Public Policies"


def is_local_mode() -> bool:
    """Check if we should use local filesystem (local dev) or Supabase (Vercel)."""
    return POLICIES_DIR.exists() and not is_supabase_configured()


@app.get("/")
async def root():
    return {"status": "ok", "mode": "local" if is_local_mode() else "supabase"}


@app.get("/policies", response_model=PoliciesResponse)
async def list_policies():
    if is_local_mode():
        # Local filesystem mode
        if not POLICIES_DIR.exists():
            raise HTTPException(status_code=404, detail="Policies directory not found")
        
        folders = []
        total_files = 0
        
        for folder_path in sorted(POLICIES_DIR.iterdir()):
            if folder_path.is_dir():
                pdf_count = len(list(folder_path.glob("*.pdf")))
                folders.append(PolicyFolder(name=folder_path.name, file_count=pdf_count))
                total_files += pdf_count
        
        return PoliciesResponse(folders=folders, total_files=total_files)
    else:
        # Supabase mode
        folders_data = list_policy_folders()
        if not folders_data:
            raise HTTPException(status_code=404, detail="No policies found in storage")
        
        folders = [PolicyFolder(name=f["name"], file_count=f["file_count"]) for f in folders_data]
        total_files = sum(f["file_count"] for f in folders_data)
        
        return PoliciesResponse(folders=folders, total_files=total_files)


@app.get("/policies/{folder_name}", response_model=FolderContentsResponse)
async def get_folder_contents(folder_name: str):
    if is_local_mode():
        # Local filesystem mode
        folder_path = POLICIES_DIR / folder_name
        
        if not folder_path.exists():
            raise HTTPException(status_code=404, detail=f"Folder '{folder_name}' not found")
        
        files = [
            PolicyFile(name=p.name, folder=folder_name, path=str(p.relative_to(POLICIES_DIR.parent)))
            for p in sorted(folder_path.glob("*.pdf"))
        ]
        
        return FolderContentsResponse(folder=folder_name, files=files)
    else:
        # Supabase mode
        files_data = list_folder_files(folder_name)
        if not files_data:
            raise HTTPException(status_code=404, detail=f"Folder '{folder_name}' not found or empty")
        
        files = [PolicyFile(name=f["name"], folder=f["folder"], path=f["path"]) for f in files_data]
        
        return FolderContentsResponse(folder=folder_name, files=files)


@app.get("/policies/{folder_name}/{file_name}/text")
async def get_pdf_text(folder_name: str, file_name: str):
    """Get extracted text from a PDF file."""
    if not file_name.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files supported")
    
    if is_local_mode():
        # Local filesystem mode
        file_path = POLICIES_DIR / folder_name / file_name
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {file_name}")
        
        try:
            pages = extract_text_from_pdf(file_path)
            return pages
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to extract text: {str(e)}")
    else:
        # Supabase mode - download to temp file first
        tmp_path = download_pdf_to_temp(folder_name, file_name)
        if not tmp_path:
            raise HTTPException(status_code=404, detail=f"File not found: {file_name}")
        
        try:
            pages = extract_text_from_pdf(tmp_path)
            return pages
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to extract text: {str(e)}")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


@app.get("/index/stats")
async def get_index_stats():
    try:
        engine = get_search_engine()
        return engine.get_stats()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Index not found. Run 'npm run index' first.")


@app.post("/analyze/stream")
async def analyze_stream(file: UploadFile = File(...)):
    """
    Stream analysis results with optimized flow:
    1. Extract questions from PDF
    2. Extract keywords for ALL questions in parallel (async)
    3. Search ALL keywords at once (batch, instant)
    4. Answer ALL questions in parallel (async), streaming results
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files supported")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    async def generate():
        try:
            # Step 1: Extract questions from PDF
            yield f"data: {json.dumps({'type': 'phase', 'phase': 'extracting', 'message': 'Extracting questions from PDF...'})}\n\n"
            
            questions = extract_questions_from_pdf(tmp_path)
            
            if not questions:
                yield f"data: {json.dumps({'type': 'error', 'message': 'No questions found. Questions should end with ?'})}\n\n"
                return
            
            # Send all questions to frontend immediately
            yield f"data: {json.dumps({'type': 'questions', 'questions': questions, 'total': len(questions)})}\n\n"
            
            # Step 2: Extract keywords for ALL questions in parallel
            yield f"data: {json.dumps({'type': 'phase', 'phase': 'keywords', 'message': f'Generating keywords for {len(questions)} questions...'})}\n\n"
            
            all_keywords = await extract_all_keywords_parallel(questions)
            
            # Step 3: Search ALL at once (batch search - instant)
            yield f"data: {json.dumps({'type': 'phase', 'phase': 'searching', 'message': 'Searching policy database...'})}\n\n"
            
            engine = get_search_engine()
            all_evidence = engine.search_batch(all_keywords, top_k_per_query=6)
            
            # Log search results for debugging
            for i, (kw, ev) in enumerate(zip(all_keywords, all_evidence)):
                print(f"Q{i+1} keywords: {kw[:5]}... -> {len(ev)} chunks found")
            
            # Step 4: Analyze compliance
            yield f"data: {json.dumps({'type': 'phase', 'phase': 'analyzing', 'message': 'Analyzing compliance for each question...'})}\n\n"
            
            # Step 4: Answer ALL questions in parallel, streaming results
            answered = 0
            met = 0
            not_met = 0
            partial = 0
            
            async for idx, answer in answer_all_questions_streaming(questions, all_evidence):
                answered += 1
                if answer.status == ComplianceStatus.MET:
                    met += 1
                elif answer.status == ComplianceStatus.NOT_MET:
                    not_met += 1
                else:
                    partial += 1
                
                yield f"data: {json.dumps({'type': 'answer', 'index': idx, 'answer': answer.model_dump(), 'progress': {'answered': answered, 'total': len(questions), 'met': met, 'not_met': not_met, 'partial': partial}})}\n\n"
            
            # Complete
            yield f"data: {json.dumps({'type': 'complete', 'total': len(questions), 'met': met, 'not_met': not_met, 'partial': partial})}\n\n"
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Analysis error: {error_details}")
            error_msg = str(e)
            if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
                error_msg = "OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
        finally:
            os.unlink(tmp_path)
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Content-Encoding": "none",  # Prevent compression buffering
        }
    )


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(file: UploadFile = File(...)):
    """Non-streaming analysis endpoint."""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files supported")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        questions = extract_questions_from_pdf(tmp_path)
        
        if not questions:
            raise HTTPException(status_code=400, detail="No questions found")
        
        # Parallel keyword extraction
        all_keywords = await extract_all_keywords_parallel(questions)
        
        # Batch search
        engine = get_search_engine()
        all_evidence = engine.search_batch(all_keywords, top_k_per_query=6)
        
        # Parallel answering
        answers = []
        async for idx, answer in answer_all_questions_streaming(questions, all_evidence):
            answers.append((idx, answer))
        
        answers.sort(key=lambda x: x[0])
        sorted_answers = [a for _, a in answers]
        
        met = sum(1 for a in sorted_answers if a.status == ComplianceStatus.MET)
        not_met = sum(1 for a in sorted_answers if a.status == ComplianceStatus.NOT_MET)
        
        return AnalysisResponse(
            answers=sorted_answers,
            total_questions=len(questions),
            met_count=met,
            not_met_count=not_met
        )
        
    finally:
        os.unlink(tmp_path)
