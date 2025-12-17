from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
import faiss

from ml_service.config import settings


class FAISSRetriever:
    """FAISS-based vector retriever for exemplar storage and search"""
    
    def __init__(self):
        settings.ensure_directories()
        self.index_dir = Path(settings.index_dir)
        self.dimension = settings.embedding_dim
        
                                      
        self.index: Optional[faiss.IndexFlatIP] = None
        self.id_map: Optional[faiss.IndexIDMap] = None
        self.metadata: Dict[int, Dict[str, Any]] = {}
        self._next_id: int = 0
        
                                          
        self._load()
    
    def _index_path(self) -> Path:
        return self.index_dir / "faiss.index"
    
    def _metadata_path(self) -> Path:
        return self.index_dir / "metadata.json"
    
    def _load(self):
        """Load index and metadata from disk"""
        index_path = self._index_path()
        metadata_path = self._metadata_path()
        
        if index_path.exists():
            self.id_map = faiss.read_index(str(index_path))
            self.index = self.id_map
        else:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.id_map = faiss.IndexIDMap(self.index)
        
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                data = json.load(f)
                                                 
                self.metadata = {int(k): v for k, v in data.get("metadata", {}).items()}
                self._next_id = data.get("next_id", 0)
    
    def _save(self):
        """Save index and metadata to disk"""
        print(f"[RETRIEVER] Saving to {self._index_path()} and {self._metadata_path()}")
        print(f"[RETRIEVER] FAISS index has {self.id_map.ntotal} vectors, metadata has {len(self.metadata)} entries")
        
        faiss.write_index(self.id_map, str(self._index_path()))
        
        with open(self._metadata_path(), 'w') as f:
            json.dump({
                "metadata": {str(k): v for k, v in self.metadata.items()},
                "next_id": self._next_id
            }, f, indent=2)
        print("[RETRIEVER] Save complete")
    
    def add(
        self,
        embedding: np.ndarray,
        document_id: str,
        text: str,
        label: str,
        span_start: int,
        span_end: int,
        **extra_metadata
    ) -> int:
        """
        Add an exemplar to the index
        
        Args:
            embedding: Vector embedding (1D numpy array)
            document_id: Source document ID
            text: The annotated text span
            label: Annotation label
            span_start: Start position of span
            span_end: End position of span
            **extra_metadata: Additional metadata to store
            
        Returns:
            ID of the added exemplar
        """
        exemplar_id = self._next_id
        self._next_id += 1
        
                      
        embedding_2d = embedding.reshape(1, -1).astype(np.float32)
        self.id_map.add_with_ids(embedding_2d, np.array([exemplar_id], dtype=np.int64))
        
                        
        self.metadata[exemplar_id] = {
            "document_id": document_id,
            "text": text,
            "label": label,
            "span_start": span_start,
            "span_end": span_end,
            **extra_metadata
        }
        
        self._save()
        return exemplar_id
    
    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
        label_filter: Optional[str] = None
    ) -> List[Tuple[int, float, Dict[str, Any]]]:
        """
        Search for similar exemplars
        
        Args:
            query_embedding: Query vector
            k: Number of results to return
            label_filter: Optional filter by label
            
        Returns:
            List of (id, score, metadata) tuples
        """
        if self.id_map.ntotal == 0:
            return []
        
                                  
        search_k = k * 3 if label_filter else k
        search_k = min(search_k, self.id_map.ntotal)
        
        print(f"[RETRIEVER] Searching FAISS index (k={search_k}, total={self.id_map.ntotal})...")
        query_2d = query_embedding.reshape(1, -1).astype(np.float32)
        scores, ids = self.id_map.search(query_2d, search_k)
        print(f"[RETRIEVER] FAISS search complete, got {len(ids[0])} results")
        
        results = []
        for idx, score in zip(ids[0], scores[0]):
            if idx == -1:
                continue
            
            metadata = self.metadata.get(int(idx), {})
            
                                
            if label_filter and metadata.get("label") != label_filter:
                continue
            
            results.append((int(idx), float(score), metadata))
            
            if len(results) >= k:
                break
        
        return results
    
    def get(self, exemplar_id: int) -> Optional[Dict[str, Any]]:
        """Get exemplar metadata by ID"""
        return self.metadata.get(exemplar_id)
    
    def remove(self, exemplar_id: int) -> bool:
        """Remove an exemplar by ID"""
        if exemplar_id not in self.metadata:
            print(f"[RETRIEVER] ID {exemplar_id} not in metadata")
            return False
        
        meta = self.metadata[exemplar_id]
        print(f"[RETRIEVER] Removing ID {exemplar_id}: '{meta.get('text')}' as {meta.get('label')}")
        
                                 
        try:
            ids_to_remove = np.array([exemplar_id], dtype=np.int64)
            n_removed = self.id_map.remove_ids(ids_to_remove)
            print(f"[RETRIEVER] FAISS removed {n_removed} vectors")
        except Exception as e:
            print(f"[RETRIEVER] Warning: Could not remove from FAISS index: {e}")
        
                              
        del self.metadata[exemplar_id]
        self._save()
        print(f"[RETRIEVER] Saved. Total now: {len(self.metadata)}")
        return True
    
    def remove_by_text_and_label(self, text: str, label: str) -> int:
        """Remove all exemplars matching text and label. Returns count removed."""
                                                           
        to_remove = []
        for eid, meta in list(self.metadata.items()):
            if meta.get("text") == text and meta.get("label") == label:
                to_remove.append(eid)
        
        print(f"[RETRIEVER] Found {len(to_remove)} exemplars matching '{text}' / {label}")
        
        for eid in to_remove:
            self.remove(eid)
        
        return len(to_remove)
    
    def count(self) -> int:
        """Return total number of exemplars"""
        return self.id_map.ntotal if self.id_map else 0
    
    def get_all_labels(self) -> List[str]:
        """Get all unique labels in the index"""
        labels = set()
        for meta in self.metadata.values():
            if "label" in meta:
                labels.add(meta["label"])
        return sorted(labels)


           
_retriever: Optional[FAISSRetriever] = None


def get_retriever() -> FAISSRetriever:
    global _retriever
    if _retriever is None:
        _retriever = FAISSRetriever()
    return _retriever

