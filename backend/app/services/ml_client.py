from __future__ import annotations

import httpx
from typing import List, Dict, Any, Optional

from backend.app.config import settings


class MLServiceClient:
    """Client for calling the ML inference service"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.ml_service_url
        self.timeout = 120.0                                               
    
    async def health(self) -> bool:
        """Check if ML service is available"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/health",
                    timeout=5.0
                )
                return response.status_code == 200
        except Exception:
            return False
    
    async def suggest(
        self,
        text: str,
        task: str = "ner",
        labels: Optional[List[str]] = None,
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        Get annotation suggestions from ML service
        
        Args:
            text: Text to annotate
            task: Task type (ner or classification)
            labels: Available labels
            top_k: Number of exemplars to use
            
        Returns:
            Dict with suggestions and metadata
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/suggest",
                json={
                    "text": text,
                    "task": task,
                    "labels": labels,
                    "top_k": top_k
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
    
    async def add_exemplar(
        self,
        document_id: str,
        text: str,
        label: str,
        span_start: int,
        span_end: int,
        context: str = "",
        rationale: str = ""
    ) -> Dict[str, Any]:
        """
        Add an approved annotation as an exemplar
        
        Returns:
            Dict with exemplar_id and total_exemplars
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/exemplars",
                json={
                    "document_id": document_id,
                    "text": text,
                    "label": label,
                    "span_start": span_start,
                    "span_end": span_end,
                    "context": context,
                    "rationale": rationale
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
    
    async def search(
        self,
        text: str,
        k: int = 5,
        label_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Search for similar exemplars"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/search",
                json={
                    "text": text,
                    "k": k,
                    "label_filter": label_filter
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get ML service statistics"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/stats",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
    
    async def delete_exemplar(self, text: str, label: str) -> Dict[str, Any]:
        """Delete exemplars matching text and label from FAISS"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/exemplars/delete",
                json={
                    "text": text,
                    "label": label
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()


           
_ml_client: Optional[MLServiceClient] = None


def get_ml_client() -> MLServiceClient:
    global _ml_client
    if _ml_client is None:
        _ml_client = MLServiceClient()
    return _ml_client

