"""Core data contracts for the Support Knowledge Copilot.

Phase 1 of the build guide: define the assistant contract and metadata rules.
Input is a user question; output is an answer, citations, a confidence score,
and an explicit "what I could not verify" section.
"""
from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class DocType(str, Enum):
    faq = "faq"
    troubleshooting = "troubleshooting"
    onboarding = "onboarding"
    api_docs = "api_docs"
    release_notes = "release_notes"
    policy = "policy"


class AccessLevel(str, Enum):
    public = "public"
    internal = "internal"
    restricted = "restricted"


# Ordering used to enforce access control during retrieval (Phase 1 audit
# finding): a requester may see chunks at their own clearance level or below.
ACCESS_RANK: dict[AccessLevel, int] = {
    AccessLevel.public: 0,
    AccessLevel.internal: 1,
    AccessLevel.restricted: 2,
}


class DocFormat(str, Enum):
    markdown = "markdown"
    html = "html"
    text = "text"
    pdf = "pdf"


class NormalizedDocument(BaseModel):
    """Output of ingestion normalization (Phase 2, step 1): both the raw
    source text and the cleaned/normalized text are kept so indexing issues
    can be debugged by diffing the two."""
    source_name: str
    doc_format: DocFormat
    raw_text: str
    cleaned_text: str
    page_count: int | None = None


class ChunkMetadata(BaseModel):
    """Metadata rules (Phase 1, step 3): stored from the very beginning so
    retrieval can be filtered later."""
    source_name: str
    section_heading: str = ""
    last_updated: date | None = None
    doc_type: DocType
    access_level: AccessLevel = AccessLevel.internal


class Chunk(BaseModel):
    chunk_id: str
    text: str
    metadata: ChunkMetadata
    chunking_strategy: str = "heading"  # track strategy for later comparison


class RetrievedChunk(BaseModel):
    chunk: Chunk
    dense_score: float | None = None
    sparse_rank: int | None = None
    fused_score: float | None = None
    rerank_score: float | None = None


class Citation(BaseModel):
    chunk_id: str
    claim: str
    supported: bool | None = None          # set by citation verifier (Phase 4)
    evidence_span: str | None = None


class ConfidenceBreakdown(BaseModel):
    retrieval_score: float = 0.0
    citation_support_rate: float = 0.0
    answer_completeness: float = 0.0
    no_answer_detected: bool = False
    final: float = 0.0


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    strategy: str = "hybrid"  # hybrid | dense | sparse — for eval comparison
    access_level: AccessLevel = AccessLevel.internal  # requester's clearance for retrieval filtering


class AskResponse(BaseModel):
    """The assistant contract's output shape."""
    answer: str
    citations: list[Citation] = []
    confidence: ConfidenceBreakdown
    could_not_verify: list[str] = []
    retrieved: list[RetrievedChunk] = []
