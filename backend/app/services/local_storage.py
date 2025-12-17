from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import uuid

from backend.app.config import settings


class LocalStorageService:
    """Simple local file storage for documents and annotations"""
    
    def __init__(self):
        settings.ensure_directories()
        self.documents_dir = Path(settings.documents_dir)
        self.annotations_dir = Path(settings.annotations_dir)
    
                                               
    
    def save_document(self, filename: str, content: bytes) -> dict:
        """Save a document and return its metadata"""
        doc_id = str(uuid.uuid4())[:8]
        
                                   
        doc_dir = self.documents_dir / doc_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        
                      
        file_path = doc_dir / filename
        with open(file_path, 'wb') as f:
            f.write(content)
        
                       
        metadata = {
            "id": doc_id,
            "filename": filename,
            "title": filename,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "file_path": str(file_path)
        }
        
        metadata_path = doc_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return metadata
    
    def get_document(self, doc_id: str) -> Optional[dict]:
        """Get document metadata"""
        metadata_path = self.documents_dir / doc_id / "metadata.json"
        if not metadata_path.exists():
            return None
        
        with open(metadata_path, 'r') as f:
            return json.load(f)
    
    def get_document_content(self, doc_id: str) -> Optional[str]:
        """Get document content as text"""
        metadata = self.get_document(doc_id)
        if not metadata:
            return None
        
        file_path = Path(metadata["file_path"])
        if not file_path.exists():
            return None
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    
    def list_documents(self) -> List[dict]:
        """List all documents"""
        documents = []
        
        if not self.documents_dir.exists():
            return documents
        
        for doc_dir in self.documents_dir.iterdir():
            if doc_dir.is_dir():
                metadata_path = doc_dir / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path, 'r') as f:
                        documents.append(json.load(f))
        
                                           
        documents.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return documents
    
    def update_document_status(self, doc_id: str, status: str) -> Optional[dict]:
        """Update document status"""
        metadata = self.get_document(doc_id)
        if not metadata:
            return None
        
        metadata["status"] = status
        metadata_path = self.documents_dir / doc_id / "metadata.json"
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return metadata
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document and its annotations"""
        doc_dir = self.documents_dir / doc_id
        if not doc_dir.exists():
            return False
        
        import shutil
        shutil.rmtree(doc_dir)
        
                                 
        ann_file = self.annotations_dir / f"{doc_id}.json"
        if ann_file.exists():
            ann_file.unlink()
        
        return True
    
                                                 
    
    def save_annotation(self, doc_id: str, annotation: dict) -> dict:
        """Save an annotation for a document"""
                                   
        annotations = self.get_annotations(doc_id)
        
                               
        if "id" not in annotation:
            annotation["id"] = str(uuid.uuid4())[:8]
        
        annotation["document_id"] = doc_id
        annotation["created_at"] = datetime.now().isoformat()
        
        annotations.append(annotation)
        
                      
        ann_file = self.annotations_dir / f"{doc_id}.json"
        with open(ann_file, 'w') as f:
            json.dump(annotations, f, indent=2)
        
        return annotation
    
    def get_annotations(self, doc_id: str) -> List[dict]:
        """Get all annotations for a document"""
        ann_file = self.annotations_dir / f"{doc_id}.json"
        if not ann_file.exists():
            return []
        
        with open(ann_file, 'r') as f:
            return json.load(f)
    
    def update_annotation(self, doc_id: str, ann_id: str, updates: dict) -> Optional[dict]:
        """Update an annotation"""
        annotations = self.get_annotations(doc_id)
        
        for i, ann in enumerate(annotations):
            if ann["id"] == ann_id:
                annotations[i] = {**ann, **updates}
                
                ann_file = self.annotations_dir / f"{doc_id}.json"
                with open(ann_file, 'w') as f:
                    json.dump(annotations, f, indent=2)
                
                return annotations[i]
        
        return None
    
    def delete_annotation(self, doc_id: str, ann_id: str) -> bool:
        """Delete an annotation"""
        annotations = self.get_annotations(doc_id)
        
        new_annotations = [ann for ann in annotations if ann["id"] != ann_id]
        
        if len(new_annotations) == len(annotations):
            return False             
        
        ann_file = self.annotations_dir / f"{doc_id}.json"
        with open(ann_file, 'w') as f:
            json.dump(new_annotations, f, indent=2)
        
        return True


           
_storage: Optional[LocalStorageService] = None


def get_storage() -> LocalStorageService:
    global _storage
    if _storage is None:
        _storage = LocalStorageService()
    return _storage

