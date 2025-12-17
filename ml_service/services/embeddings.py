from __future__ import annotations

from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer

from ml_service.config import settings


class EmbeddingService:
    """Service for generating text embeddings"""
    
    _instance: "EmbeddingService | None" = None
    _model: SentenceTransformer | None = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def _get_model(self) -> SentenceTransformer:
        """Lazy load the model"""
        if self._model is None:
            print(f"Loading embedding model: {settings.embedding_model}")
            self._model = SentenceTransformer(settings.embedding_model)
        return self._model
    
    def embed(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            numpy array of shape (n_texts, embedding_dim)
        """
        model = self._get_model()
        embeddings = model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True
        )
        return embeddings.astype(np.float32)
    
    def embed_single(self, text: str) -> np.ndarray:
        """Embed a single text and return 1D array"""
        return self.embed([text])[0]
    
    @property
    def dimension(self) -> int:
        """Return embedding dimension"""
        return settings.embedding_dim


def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()

