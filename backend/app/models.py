from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class ComplianceStatus(str, Enum):
    MET = "MET"
    NOT_MET = "NOT_MET"
    PARTIAL = "PARTIAL"


# Request/Response models for API
class PolicyFolder(BaseModel):
    name: str
    file_count: int


class PolicyFile(BaseModel):
    name: str
    folder: str
    path: str


class PoliciesResponse(BaseModel):
    folders: list[PolicyFolder]
    total_files: int


class FolderContentsResponse(BaseModel):
    folder: str
    files: list[PolicyFile]


class QuestionKeywords(BaseModel):
    question: str
    keywords: list[str]


class KeywordExtractionResponse(BaseModel):
    questions: list[QuestionKeywords]


class ChunkMatch(BaseModel):
    chunk_id: str
    source: str
    page: int
    text: str
    score: float


class ComplianceAnswer(BaseModel):
    question: str
    status: ComplianceStatus
    evidence: Optional[str] = None
    source: Optional[str] = None
    page: Optional[int] = None
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


class AnalysisResponse(BaseModel):
    answers: list[ComplianceAnswer]
    total_questions: int
    met_count: int
    not_met_count: int


# Internal models for indexing
class TextChunk(BaseModel):
    id: str
    source: str
    folder: str
    page: int
    text: str
    keywords: list[str]


class PolicyIndex(BaseModel):
    chunks: list[TextChunk]
    inverted_index: dict[str, list[str]]
    metadata: dict[str, str]
