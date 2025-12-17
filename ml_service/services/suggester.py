"""
Annotation Suggester - RAG + ICL Pipeline
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
import numpy as np

from .embeddings import get_embedding_service
from .retriever import get_retriever
from .llm_client import get_llm_client, parse_json_response
from .prompts import build_ner_prompt, build_classification_prompt
from .style_scorer import get_style_scorer


class AnnotationSuggester:
    """
    Main service for generating annotation suggestions using RAG + ICL
    with style-based re-ranking.
    """
    
    def __init__(self):
        self.embeddings = get_embedding_service()
        self.retriever = get_retriever()
        self.llm = get_llm_client()
        self.style_scorer = get_style_scorer()
    
    def suggest(
        self,
        text: str,
        task: str = "ner",
        labels: Optional[List[str]] = None,
        top_k: int = 5,
        annotator_id: Optional[str] = None,
        enable_style_ranking: bool = True
    ) -> Dict[str, Any]:
        """
        Generate annotation suggestions using RAG + ICL with style ranking.
        
        Args:
            text: Text to annotate
            task: Task type ("ner" or "classification")
            labels: Available labels
            top_k: Number of exemplars to retrieve for ICL
            annotator_id: Current annotator for style matching
            enable_style_ranking: Whether to apply style-based re-ranking
            
        Returns:
            Dict with:
            - suggestions: Ranked list of suggestions
            - exemplars_used: Number of exemplars in prompt
            - style_scores: Aggregate style metrics
        """
                        
        if labels is None:
            labels = ["ORG", "PERSON", "LOCATION", "DATE", "OTHER"]
        
                                                            
        print("[SUGGESTER] Step 1: Embedding query text...")
        query_embedding = self.embeddings.embed_single(text)
        print("[SUGGESTER] Step 1: Done")
        
                                                                            
        print("[SUGGESTER] Step 2: Retrieving exemplars...")
        exemplars = []
        exemplar_embeddings = []
        
        if self.retriever.count() > 0:
            results = self.retriever.search(query_embedding, k=top_k)
            for _, score, meta in results:
                exemplars.append({
                    **meta,
                    "retrieval_score": score
                })
                                                    
                ex_embedding = self.embeddings.embed_single(
                    f"[{meta.get('label', '')}] {meta.get('text', '')}"
                )
                exemplar_embeddings.append(ex_embedding)
        print(f"[SUGGESTER] Step 2: Retrieved {len(exemplars)} exemplars")
        
                                                                                     
        print("[SUGGESTER] Step 3: Building prompt...")
        if task == "ner":
            system_prompt, user_prompt = build_ner_prompt(text, labels, exemplars)
        else:
            system_prompt, user_prompt = build_classification_prompt(text, labels, exemplars)
        print(f"[SUGGESTER] Step 3: Prompt built (user prompt length: {len(user_prompt)})")
        
                                                                        
        print("[SUGGESTER] Step 4: Calling LLM...")
        raw_response = self.llm.complete(system_prompt, user_prompt)
        print(f"[SUGGESTER] Step 4: LLM responded ({len(raw_response)} chars)")
        
                                                              
        parsed = parse_json_response(raw_response)
        
        suggestions = []
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    suggestions.append({
                        "text": item.get("text", ""),
                        "label": item.get("label", ""),
                        "span_start": item.get("start", 0),
                        "span_end": item.get("end", 0),
                        "confidence": item.get("confidence", 0.7),
                        "rationale": item.get("rationale", ""),
                        "source": "ai"
                    })
        elif isinstance(parsed, dict):
            suggestions.append({
                "label": parsed.get("label", ""),
                "confidence": parsed.get("confidence", 0.7),
                "rationale": parsed.get("rationale", ""),
                "source": "ai"
            })
        
                                                                                
        style_stats = {
            "enabled": enable_style_ranking,
            "annotator_id": annotator_id,
            "avg_content_similarity": 0.0,
            "avg_label_similarity": 0.0,
            "avg_style_similarity": 0.0
        }
        
        if enable_style_ranking and suggestions:
                                                    
            suggestions = self.style_scorer.rank_suggestions(
                suggestions=suggestions,
                context=text,
                exemplar_embeddings=exemplar_embeddings,
                annotator_id=annotator_id
            )
            
                                           
            if suggestions:
                content_sims = [s.get("style_scores", {}).get("content_similarity", 0) for s in suggestions]
                label_sims = [s.get("style_scores", {}).get("label_similarity", 0) for s in suggestions]
                style_sims = [s.get("style_scores", {}).get("style_similarity", 0) for s in suggestions]
                
                style_stats["avg_content_similarity"] = sum(content_sims) / len(content_sims)
                style_stats["avg_label_similarity"] = sum(label_sims) / len(label_sims)
                style_stats["avg_style_similarity"] = sum(style_sims) / len(style_sims)
        
        return {
            "suggestions": suggestions,
            "exemplars_used": len(exemplars),
            "exemplars": [
                {"text": e.get("text", ""), "label": e.get("label", ""), "score": e.get("retrieval_score", 0)}
                for e in exemplars
            ],
            "style_ranking": style_stats,
            "raw_response": raw_response
        }
    
    def add_exemplar(
        self,
        document_id: str,
        text: str,
        label: str,
        span_start: int,
        span_end: int,
        context: str = "",
        rationale: str = "",
        annotator_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add an approved annotation as an exemplar and update style profiles.
        
        This implements the continuous learning aspect:
        - Add to FAISS for future retrieval
        - Update label centroids for label similarity
        - Update annotator profile for style similarity
        
        Args:
            document_id: Source document ID
            text: The annotated text span
            label: Annotation label
            span_start: Start position
            span_end: End position
            context: Surrounding context
            rationale: Annotator's explanation
            annotator_id: Who made this annotation
            
        Returns:
            Dict with exemplar_id and updated stats
        """
                                             
        embed_text = f"{context} {text}" if context else text
        content_embedding = self.embeddings.embed_single(embed_text)
        
                                                        
        style_embedding = self.style_scorer.create_annotation_embedding(
            text=text,
            label=label,
            context=context,
            rationale=rationale
        )
        
                                
        exemplar_id = self.retriever.add(
            embedding=content_embedding,
            document_id=document_id,
            text=text,
            label=label,
            span_start=span_start,
            span_end=span_end,
            context=context,
            rationale=rationale,
            annotator_id=annotator_id or "default"
        )
        
                               
        self.style_scorer.update_label_centroid(label, style_embedding)
        
                                  
        if annotator_id:
            self.style_scorer.update_annotator_profile(
                annotator_id=annotator_id,
                embedding=style_embedding,
                label=label
            )
        
        return {
            "exemplar_id": exemplar_id,
            "total_exemplars": self.retriever.count(),
            "label_count": self.style_scorer.label_counts.get(label, 0),
            "style_stats": self.style_scorer.get_stats()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get combined retriever and style statistics"""
        retriever_stats = {
            "total_exemplars": self.retriever.count(),
            "labels_in_index": self.retriever.get_all_labels()
        }
        
        style_stats = self.style_scorer.get_stats()
        
        return {
            "retriever": retriever_stats,
            "style_scorer": style_stats,
            "embedding_model": self.embeddings._get_model().get_sentence_embedding_dimension()
        }


           
_suggester: Optional[AnnotationSuggester] = None


def get_suggester() -> AnnotationSuggester:
    global _suggester
    if _suggester is None:
        _suggester = AnnotationSuggester()
    return _suggester
