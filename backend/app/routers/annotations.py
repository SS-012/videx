from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from backend.app.services.local_storage import get_storage
from backend.app.services.ml_client import get_ml_client

router = APIRouter(prefix="/annotations", tags=["annotations"])


class CreateAnnotationRequest(BaseModel):
    label: str
    span_start: int
    span_end: int
    text: Optional[str] = None
    confidence: float = 1.0
    source: str = "manual"                


class UpdateAnnotationRequest(BaseModel):
    label: Optional[str] = None
    span_start: Optional[int] = None
    span_end: Optional[int] = None
    text: Optional[str] = None
    confidence: Optional[float] = None


class AnnotationOut(BaseModel):
    id: str
    document_id: str
    label: str
    span_start: int
    span_end: int
    text: Optional[str] = None
    confidence: float
    source: str
    created_at: str


@router.post("/documents/{document_id}", response_model=AnnotationOut)
async def create_annotation(document_id: str, body: CreateAnnotationRequest):
    """Create a new annotation for a document and add it as an exemplar"""
    storage = get_storage()
    
                            
    doc = storage.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    annotation = storage.save_annotation(document_id, body.model_dump())
    
                            
    if doc["status"] == "pending":
        storage.update_document_status(document_id, "in_progress")
    
                                                  
    try:
        ml_client = get_ml_client()
        if await ml_client.health():
                                              
            content = storage.get_document_content(document_id) or ""
            context_start = max(0, body.span_start - 100)
            context_end = min(len(content), body.span_end + 100)
            context = content[context_start:context_end]
            
                                                         
            rationale = f"Manual annotation" if body.source == "manual" else "Accepted AI suggestion"
            
            await ml_client.add_exemplar(
                document_id=document_id,
                text=body.text or content[body.span_start:body.span_end],
                label=body.label,
                span_start=body.span_start,
                span_end=body.span_end,
                context=context,
                rationale=rationale
            )
            print(f"[EXEMPLAR] Added from UI: '{body.text}' as {body.label}")
    except Exception as e:
        print(f"[EXEMPLAR] Failed to add from UI: {e}")
                                                              
    
    return AnnotationOut(**annotation)


@router.get("/documents/{document_id}", response_model=List[AnnotationOut])
def get_document_annotations(document_id: str):
    """Get all annotations for a document"""
    storage = get_storage()
    
                            
    doc = storage.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    annotations = storage.get_annotations(document_id)
    return [AnnotationOut(**ann) for ann in annotations]


@router.put("/documents/{document_id}/{annotation_id}", response_model=AnnotationOut)
def update_annotation(document_id: str, annotation_id: str, body: UpdateAnnotationRequest):
    """Update an annotation"""
    storage = get_storage()
    
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    annotation = storage.update_annotation(document_id, annotation_id, updates)
    
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    return AnnotationOut(**annotation)


@router.delete("/documents/{document_id}/{annotation_id}")
async def delete_annotation(document_id: str, annotation_id: str):
    """Delete an annotation and remove from FAISS"""
    storage = get_storage()
    
                                                                
    annotations = storage.get_annotations(document_id)
    annotation = next((a for a in annotations if a["id"] == annotation_id), None)
    
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")
    
                               
    storage.delete_annotation(document_id, annotation_id)
    
                            
    try:
        ml_client = get_ml_client()
        if await ml_client.health():
            result = await ml_client.delete_exemplar(
                text=annotation.get("text", ""),
                label=annotation.get("label", "")
            )
            print(f"[EXEMPLAR] Removed from FAISS: '{annotation.get('text')}' as {annotation.get('label')} (removed {result.get('removed_count', 0)})")
    except Exception as e:
        print(f"[EXEMPLAR] Failed to remove from FAISS: {e}")
                                                      
    
    return {"status": "deleted", "id": annotation_id}


@router.post("/documents/{document_id}/{annotation_id}/accept")
async def accept_pending_annotation(document_id: str, annotation_id: str):
    """Accept a pending annotation - adds to FAISS and changes status"""
    storage = get_storage()
    
                    
    annotations = storage.get_annotations(document_id)
    annotation = next((a for a in annotations if a["id"] == annotation_id), None)
    
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    if annotation.get("source") != "pending_batch":
        return {"status": "already_accepted", "id": annotation_id}
    
                               
    updated = storage.update_annotation(document_id, annotation_id, {"source": "batch_ai"})
    
                      
    try:
        ml_client = get_ml_client()
        if await ml_client.health():
            content = storage.get_document_content(document_id) or ""
            context_start = max(0, annotation["span_start"] - 100)
            context_end = min(len(content), annotation["span_end"] + 100)
            context = content[context_start:context_end]
            
            await ml_client.add_exemplar(
                document_id=document_id,
                text=annotation.get("text", ""),
                label=annotation.get("label", ""),
                span_start=annotation["span_start"],
                span_end=annotation["span_end"],
                context=context,
                rationale="Accepted batch annotation"
            )
            print(f"[EXEMPLAR] Accepted: '{annotation.get('text')}' as {annotation.get('label')}")
    except Exception as e:
        print(f"[EXEMPLAR] Failed to add after accept: {e}")
    
    return {"status": "accepted", "id": annotation_id}


@router.post("/documents/{document_id}/{annotation_id}/reject")
async def reject_pending_annotation(document_id: str, annotation_id: str):
    """Reject a pending annotation - removes it"""
    storage = get_storage()
    
                                           
    annotations = storage.get_annotations(document_id)
    annotation = next((a for a in annotations if a["id"] == annotation_id), None)
    
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")
    
               
    storage.delete_annotation(document_id, annotation_id)
    
    return {"status": "rejected", "id": annotation_id}


                                          

class SuggestRequest(BaseModel):
    task: str = "ner"
    labels: Optional[List[str]] = None
    top_k: int = 3


class SuggestionOut(BaseModel):
    text: Optional[str] = None
    label: str
    span_start: Optional[int] = None
    span_end: Optional[int] = None
    confidence: float
    source: str = "ai"


class SuggestResponse(BaseModel):
    suggestions: List[SuggestionOut]
    exemplars_used: int
    ml_available: bool


@router.post("/documents/{document_id}/suggest", response_model=SuggestResponse)
async def get_suggestions(document_id: str, body: SuggestRequest):
    """Get AI-generated annotation suggestions for a document"""
    storage = get_storage()
    
                          
    content = storage.get_document_content(document_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Document not found")
    
    ml_client = get_ml_client()
    
    try:
                                          
        if not await ml_client.health():
            return SuggestResponse(
                suggestions=[],
                exemplars_used=0,
                ml_available=False
            )
        
                                         
        result = await ml_client.suggest(
            text=content,
            task=body.task,
            labels=body.labels,
            top_k=body.top_k
        )
        
        suggestions = [SuggestionOut(**s) for s in result.get("suggestions", [])]
        
        return SuggestResponse(
            suggestions=suggestions,
            exemplars_used=result.get("exemplars_used", 0),
            ml_available=True
        )
    
    except Exception as e:
        print(f"ML service error: {e}")
        return SuggestResponse(
            suggestions=[],
            exemplars_used=0,
            ml_available=False
        )


class ApproveRequest(BaseModel):
    context: Optional[str] = ""


@router.post("/documents/{document_id}/{annotation_id}/approve")
async def approve_annotation(document_id: str, annotation_id: str, body: ApproveRequest = None):
    """Approve an annotation and add it as an exemplar for future suggestions"""
    storage = get_storage()
    
                        
    annotations = storage.get_annotations(document_id)
    annotation = next((a for a in annotations if a["id"] == annotation_id), None)
    
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    ml_client = get_ml_client()
    
    try:
        if await ml_client.health():
                                           
            result = await ml_client.add_exemplar(
                document_id=document_id,
                text=annotation.get("text", ""),
                label=annotation["label"],
                span_start=annotation["span_start"],
                span_end=annotation["span_end"],
                context=body.context if body else ""
            )
            
            return {
                "status": "approved",
                "exemplar_id": result.get("exemplar_id"),
                "total_exemplars": result.get("total_exemplars")
            }
    except Exception as e:
        print(f"ML service error: {e}")
    
    return {"status": "approved", "exemplar_id": None, "total_exemplars": None}
