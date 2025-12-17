from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional

from backend.app.services.local_storage import get_storage

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentOut(BaseModel):
    id: str
    filename: str
    title: str
    status: str
    created_at: str
    content: Optional[str] = None


class DocumentContentResponse(BaseModel):
    content: str


class UpdateStatusRequest(BaseModel):
    status: str


@router.post("/upload", response_model=DocumentOut)
async def upload_document(file: UploadFile = File(...)):
    """Upload a document for annotation"""
    storage = get_storage()
    
    content = await file.read()
    metadata = storage.save_document(file.filename, content)
    
    return DocumentOut(**metadata)


@router.post("/batch-upload", response_model=List[DocumentOut])
async def batch_upload_documents(files: List[UploadFile] = File(...)):
    """Upload multiple documents at once"""
    storage = get_storage()
    documents = []
    
    for file in files:
        content = await file.read()
        metadata = storage.save_document(file.filename, content)
        documents.append(DocumentOut(**metadata))
    
    return documents


@router.get("", response_model=List[DocumentOut])
def list_documents():
    """List all uploaded documents"""
    storage = get_storage()
    return [DocumentOut(**doc) for doc in storage.list_documents()]


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: str):
    """Get document metadata"""
    storage = get_storage()
    doc = storage.get_document(document_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentOut(**doc)


@router.get("/{document_id}/content", response_model=DocumentContentResponse)
def get_document_content(document_id: str):
    """Get document text content"""
    storage = get_storage()
    content = storage.get_document_content(document_id)
    
    if content is None:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentContentResponse(content=content)


@router.patch("/{document_id}/status", response_model=DocumentOut)
def update_document_status(document_id: str, body: UpdateStatusRequest):
    """Update document annotation status"""
    storage = get_storage()
    
    valid_statuses = ["pending", "in_progress", "completed", "reviewed"]
    if body.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    doc = storage.update_document_status(document_id, body.status)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentOut(**doc)


@router.delete("/{document_id}")
def delete_document(document_id: str):
    """Delete a document and its annotations"""
    storage = get_storage()
    
    if not storage.delete_document(document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {"status": "deleted", "id": document_id}
