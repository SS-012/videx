from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class AnnotateRequest(BaseModel):
    input_text: str = Field(..., description="Raw text to annotate")
    task: Literal["ner", "classification", "json"] = "json"
    schema: Optional[Dict[str, Any]] = None
    max_suggestions: int = 1


class AnnotationSpan(BaseModel):
    start: int
    end: int
    label: str


class AnnotationSuggestion(BaseModel):
    spans: Optional[List[AnnotationSpan]] = None
    labels: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None
    rationale: Optional[str] = None


class AnnotateResponse(BaseModel):
    suggestions: List[AnnotationSuggestion]
