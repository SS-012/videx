"""
Style-Based Similarity Scoring

These are combined into a weighted score that re-ranks the model's outputs.
"""

from __future__ import annotations

import json
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import numpy as np

from ml_service.config import settings
from ml_service.services.embeddings import get_embedding_service


class StyleScorer:
    """
    Computes style-based similarity scores for annotation consistency.
    
    Maintains:
    - Label centroids: average embedding for each label type
    - Annotator profiles: historical annotation patterns per annotator
    """
    
    def __init__(self):
        self.embeddings = get_embedding_service()
        self.data_dir = Path(settings.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Label centroids: {label: embedding vector}
        self.label_centroids: Dict[str, np.ndarray] = {}
        self.label_counts: Dict[str, int] = {}
        
        # Annotator profiles: {annotator_id: {embeddings: [], labels: []}}
        self.annotator_profiles: Dict[str, Dict[str, Any]] = {}
        
        self._load()
    
    def _centroids_path(self) -> Path:
        return self.data_dir / "label_centroids.json"
    
    def _profiles_path(self) -> Path:
        return self.data_dir / "annotator_profiles.json"
    
    def _load(self):
        """Load centroids and profiles from disk"""
        if self._centroids_path().exists():
            with open(self._centroids_path(), 'r') as f:
                data = json.load(f)
                self.label_centroids = {
                    k: np.array(v["centroid"], dtype=np.float32)
                    for k, v in data.items()
                }
                self.label_counts = {k: v["count"] for k, v in data.items()}
        
        if self._profiles_path().exists():
            with open(self._profiles_path(), 'r') as f:
                data = json.load(f)
                self.annotator_profiles = {
                    k: {
                        "embeddings": [np.array(e, dtype=np.float32) for e in v["embeddings"]],
                        "labels": v["labels"]
                    }
                    for k, v in data.items()
                }
    
    def _save(self):
        """Save centroids and profiles to disk"""
        centroids_data = {
            k: {"centroid": v.tolist(), "count": self.label_counts.get(k, 0)}
            for k, v in self.label_centroids.items()
        }
        with open(self._centroids_path(), 'w') as f:
            json.dump(centroids_data, f)
        
        profiles_data = {
            k: {
                "embeddings": [e.tolist() for e in v["embeddings"][-50:]],
                "labels": v["labels"][-50:]
            }
            for k, v in self.annotator_profiles.items()
        }
        with open(self._profiles_path(), 'w') as f:
            json.dump(profiles_data, f)
    
    def create_annotation_embedding(
        self,
        text: str,
        label: str,
        context: str = "",
        rationale: str = ""
    ) -> np.ndarray:
        """
        Create a structured embedding for an annotation.
        
        Combines text content with label and rationale for style capture.
        """
        structured_text = f"[{label}] {text}"
        if context:
            structured_text = f"{context} -> {structured_text}"
        if rationale:
            structured_text = f"{structured_text} ({rationale})"
        
        return self.embeddings.embed_single(structured_text)
    
    def update_label_centroid(self, label: str, embedding: np.ndarray):
        """
        Update the centroid for a label using online averaging.
        
        centroid = (old_centroid * count + new_embedding) / (count + 1)
        """
        if label not in self.label_centroids:
            self.label_centroids[label] = embedding.copy()
            self.label_counts[label] = 1
        else:
            count = self.label_counts[label]
            old_centroid = self.label_centroids[label]
            new_centroid = (old_centroid * count + embedding) / (count + 1)
            self.label_centroids[label] = new_centroid
            self.label_counts[label] = count + 1
        
        self._save()
    
    def update_annotator_profile(
        self,
        annotator_id: str,
        embedding: np.ndarray,
        label: str
    ):
        """Update an annotator's style profile with a new annotation"""
        if annotator_id not in self.annotator_profiles:
            self.annotator_profiles[annotator_id] = {
                "embeddings": [],
                "labels": []
            }
        
        profile = self.annotator_profiles[annotator_id]
        profile["embeddings"].append(embedding)
        profile["labels"].append(label)
        
        if len(profile["embeddings"]) > 100:
            profile["embeddings"] = profile["embeddings"][-100:]
            profile["labels"] = profile["labels"][-100:]
        
        self._save()
    
    def compute_content_similarity(
        self,
        candidate_embedding: np.ndarray,
        exemplar_embeddings: List[np.ndarray]
    ) -> float:
        """
        Compute content similarity between candidate and similar examples.
        
        Returns average cosine similarity to top exemplars.
        """
        if not exemplar_embeddings:
            return 0.0
        
        similarities = []
        for ex_emb in exemplar_embeddings:
            sim = np.dot(candidate_embedding, ex_emb)
            similarities.append(sim)
        
        return float(np.mean(similarities))
    
    def compute_label_similarity(
        self,
        label: str,
        candidate_embedding: np.ndarray
    ) -> float:
        """
        Compute similarity to label-specific centroid.
        
        Returns cosine similarity to the label's centroid, or 0 if no centroid exists.
        """
        if label not in self.label_centroids:
            return 0.5
        
        centroid = self.label_centroids[label]
        return float(np.dot(candidate_embedding, centroid))
    
    def compute_style_similarity(
        self,
        candidate_embedding: np.ndarray,
        annotator_id: Optional[str] = None
    ) -> float:
        """
        Compute style similarity to annotator's historical patterns.
        
        If no annotator specified, compares to global average.
        """
        if annotator_id and annotator_id in self.annotator_profiles:
            profile = self.annotator_profiles[annotator_id]
            if profile["embeddings"]:
                similarities = [
                    np.dot(candidate_embedding, emb)
                    for emb in profile["embeddings"][-10:]
                ]
                return float(np.mean(similarities))
        
        all_similarities = []
        for profile in self.annotator_profiles.values():
            for emb in profile["embeddings"][-5:]:
                all_similarities.append(np.dot(candidate_embedding, emb))
        
        if all_similarities:
            return float(np.mean(all_similarities))
        
        return 0.5
    
    def score_suggestion(
        self,
        text: str,
        label: str,
        context: str = "",
        rationale: str = "",
        exemplar_embeddings: List[np.ndarray] = None,
        annotator_id: Optional[str] = None,
        weights: Tuple[float, float, float] = (0.4, 0.3, 0.3)
    ) -> Dict[str, float]:
        """
        Compute combined similarity score for a suggestion.
        
        Args:
            text: The suggested text span
            label: The suggested label
            context: Surrounding context
            rationale: Model's rationale
            exemplar_embeddings: Embeddings of retrieved exemplars
            annotator_id: Current annotator for style matching
            weights: (content_weight, label_weight, style_weight)
            
        Returns:
            Dict with individual scores and combined score
        """
        candidate_embedding = self.create_annotation_embedding(
            text=text,
            label=label,
            context=context,
            rationale=rationale
        )
        
        content_sim = self.compute_content_similarity(
            candidate_embedding,
            exemplar_embeddings or []
        )
        
        label_sim = self.compute_label_similarity(label, candidate_embedding)
        
        style_sim = self.compute_style_similarity(
            candidate_embedding,
            annotator_id
        )
        
        w_content, w_label, w_style = weights
        combined = (
            content_sim * w_content +
            label_sim * w_label +
            style_sim * w_style
        )
        
        return {
            "content_similarity": content_sim,
            "label_similarity": label_sim,
            "style_similarity": style_sim,
            "combined_score": combined,
            "weights": {"content": w_content, "label": w_label, "style": w_style}
        }
    
    def rank_suggestions(
        self,
        suggestions: List[Dict[str, Any]],
        context: str = "",
        exemplar_embeddings: List[np.ndarray] = None,
        annotator_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Re-rank suggestions based on style similarity scores.
        
        Args:
            suggestions: List of suggestion dicts with text, label, etc.
            context: Document context
            exemplar_embeddings: Embeddings from retrieved exemplars
            annotator_id: Current annotator
            
        Returns:
            Suggestions sorted by combined score (highest first)
        """
        scored_suggestions = []
        
        for suggestion in suggestions:
            scores = self.score_suggestion(
                text=suggestion.get("text", ""),
                label=suggestion.get("label", ""),
                context=context,
                rationale=suggestion.get("rationale", ""),
                exemplar_embeddings=exemplar_embeddings,
                annotator_id=annotator_id
            )
            
            scored_suggestion = {
                **suggestion,
                "style_scores": scores,
                    "confidence": scores["combined_score"]
            }
            scored_suggestions.append(scored_suggestion)
        
        scored_suggestions.sort(
            key=lambda x: x["style_scores"]["combined_score"],
            reverse=True
        )
        
        return scored_suggestions
    
    def get_stats(self) -> Dict[str, Any]:
        """Get style scorer statistics"""
        return {
            "labels_tracked": list(self.label_centroids.keys()),
            "label_counts": dict(self.label_counts),
            "annotators_tracked": list(self.annotator_profiles.keys()),
            "total_annotations_tracked": sum(
                len(p["embeddings"]) for p in self.annotator_profiles.values()
            )
        }


_scorer: Optional[StyleScorer] = None


def get_style_scorer() -> StyleScorer:
    global _scorer
    if _scorer is None:
        _scorer = StyleScorer()
    return _scorer

