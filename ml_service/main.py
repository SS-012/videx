"""
ML Service - RAG + ICL Annotation Suggestions
"""

import os
import platform

if platform.system() == "Darwin":
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from ml_service.config import settings
from ml_service.services.embeddings import get_embedding_service
from ml_service.services.retriever import get_retriever
from ml_service.services.suggester import get_suggester
from ml_service.services.style_scorer import get_style_scorer

app = FastAPI(
    title=settings.app_name,
    description="RAG + ICL annotation suggestion service with style-based ranking"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


                                                    

class EmbedRequest(BaseModel):
    texts: List[str]


class EmbedResponse(BaseModel):
    embeddings: List[List[float]]
    dimension: int


class SuggestRequest(BaseModel):
    text: str
    task: str = "ner"
    labels: Optional[List[str]] = None
    top_k: int = 5
    annotator_id: Optional[str] = None
    enable_style_ranking: bool = True


class StyleScores(BaseModel):
    content_similarity: float
    label_similarity: float
    style_similarity: float
    combined_score: float


class Suggestion(BaseModel):
    text: Optional[str] = None
    label: str
    span_start: Optional[int] = None
    span_end: Optional[int] = None
    confidence: float
    source: str = "ai"
    rationale: Optional[str] = None
    style_scores: Optional[StyleScores] = None


class RetrievedExemplar(BaseModel):
    text: str
    label: str
    score: float


class StyleRankingStats(BaseModel):
    enabled: bool
    annotator_id: Optional[str]
    avg_content_similarity: float
    avg_label_similarity: float
    avg_style_similarity: float


class SuggestResponse(BaseModel):
    suggestions: List[Suggestion]
    exemplars_used: int
    exemplars: List[RetrievedExemplar]
    style_ranking: StyleRankingStats


class AddExemplarRequest(BaseModel):
    document_id: str
    text: str
    label: str
    span_start: int
    span_end: int
    context: Optional[str] = ""
    rationale: Optional[str] = ""
    annotator_id: Optional[str] = None


class AddExemplarResponse(BaseModel):
    exemplar_id: int
    total_exemplars: int
    label_count: int


class SearchRequest(BaseModel):
    text: str
    k: int = 5
    label_filter: Optional[str] = None


class SearchResult(BaseModel):
    id: int
    score: float
    text: str
    label: str
    document_id: str


class SearchResponse(BaseModel):
    results: List[SearchResult]


class ScoreRequest(BaseModel):
    text: str
    label: str
    context: Optional[str] = ""
    rationale: Optional[str] = ""
    annotator_id: Optional[str] = None


class ScoreResponse(BaseModel):
    content_similarity: float
    label_similarity: float
    style_similarity: float
    combined_score: float
    weights: Dict[str, float]


class StatsResponse(BaseModel):
    total_exemplars: int
    labels_in_index: List[str]
    labels_tracked: List[str]
    label_counts: Dict[str, int]
    annotators_tracked: List[str]
    total_annotations_tracked: int
    embedding_model: str
    llm_provider: str


                                     

@app.get("/health")
async def health():
    return {"status": "ok", "service": "ml"}


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get ML service statistics including style scoring stats"""
    suggester = get_suggester()
    stats = suggester.get_stats()
    
    return StatsResponse(
        total_exemplars=stats["retriever"]["total_exemplars"],
        labels_in_index=stats["retriever"]["labels_in_index"],
        labels_tracked=stats["style_scorer"]["labels_tracked"],
        label_counts=stats["style_scorer"]["label_counts"],
        annotators_tracked=stats["style_scorer"]["annotators_tracked"],
        total_annotations_tracked=stats["style_scorer"]["total_annotations_tracked"],
        embedding_model=settings.embedding_model,
        llm_provider=settings.llm_provider
    )


@app.post("/embed", response_model=EmbedResponse)
async def embed_texts(request: EmbedRequest):
    """Generate embeddings for texts"""
    if not request.texts:
        raise HTTPException(status_code=400, detail="No texts provided")
    
    embeddings = get_embedding_service()
    vectors = embeddings.embed(request.texts)
    
    return EmbedResponse(
        embeddings=vectors.tolist(),
        dimension=embeddings.dimension
    )


@app.post("/suggest", response_model=SuggestResponse)
async def suggest_annotations(request: SuggestRequest):
    """
    Generate annotation suggestions using RAG + ICL with style ranking.
    
    Implements Sections 3.2 and 3.3 of the methodology:
    1. Embed input text
    2. Retrieve similar exemplars (RAG)
    3. Format as structured annotation blocks (ICL)
    4. Generate suggestions via LLM
    5. Re-rank by style similarity scores
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="No text provided")
    
    print(f"[SUGGEST] Starting suggest for text: {request.text[:50]}...")
    print(f"[SUGGEST] Labels: {request.labels}, top_k: {request.top_k}")
    
    try:
        suggester = get_suggester()
        print("[SUGGEST] Got suggester, calling suggest()...")
        result = suggester.suggest(
            text=request.text,
            task=request.task,
            labels=request.labels,
            top_k=request.top_k,
            annotator_id=request.annotator_id,
            enable_style_ranking=request.enable_style_ranking
        )
        print(f"[SUGGEST] Got {len(result.get('suggestions', []))} suggestions")
    except Exception as e:
        print(f"[SUGGEST] ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise
    
                        
    suggestions = []
    for s in result["suggestions"]:
        style_scores = None
        if "style_scores" in s:
            style_scores = StyleScores(
                content_similarity=s["style_scores"].get("content_similarity", 0),
                label_similarity=s["style_scores"].get("label_similarity", 0),
                style_similarity=s["style_scores"].get("style_similarity", 0),
                combined_score=s["style_scores"].get("combined_score", 0)
            )
        
        suggestions.append(Suggestion(
            text=s.get("text"),
            label=s.get("label", ""),
            span_start=s.get("span_start"),
            span_end=s.get("span_end"),
            confidence=s.get("confidence", 0.7),
            source=s.get("source", "ai"),
            rationale=s.get("rationale"),
            style_scores=style_scores
        ))
    
                      
    exemplars = [
        RetrievedExemplar(text=e["text"], label=e["label"], score=e["score"])
        for e in result.get("exemplars", [])
    ]
    
                        
    style_stats = result.get("style_ranking", {})
    style_ranking = StyleRankingStats(
        enabled=style_stats.get("enabled", False),
        annotator_id=style_stats.get("annotator_id"),
        avg_content_similarity=style_stats.get("avg_content_similarity", 0),
        avg_label_similarity=style_stats.get("avg_label_similarity", 0),
        avg_style_similarity=style_stats.get("avg_style_similarity", 0)
    )
    
    return SuggestResponse(
        suggestions=suggestions,
        exemplars_used=result["exemplars_used"],
        exemplars=exemplars,
        style_ranking=style_ranking
    )


@app.post("/exemplars", response_model=AddExemplarResponse)
async def add_exemplar(request: AddExemplarRequest):
    """
    Add an approved annotation as an exemplar.
    
    This updates:
    - FAISS index for future retrieval
    - Label centroids for label similarity
    - Annotator profile for style similarity
    """
    suggester = get_suggester()
    result = suggester.add_exemplar(
        document_id=request.document_id,
        text=request.text,
        label=request.label,
        span_start=request.span_start,
        span_end=request.span_end,
        context=request.context or "",
        rationale=request.rationale or "",
        annotator_id=request.annotator_id
    )
    
    return AddExemplarResponse(
        exemplar_id=result["exemplar_id"],
        total_exemplars=result["total_exemplars"],
        label_count=result["label_count"]
    )


class DeleteExemplarRequest(BaseModel):
    text: str
    label: str


class DeleteExemplarResponse(BaseModel):
    removed_count: int
    total_exemplars: int


@app.post("/exemplars/delete", response_model=DeleteExemplarResponse)
async def delete_exemplar(request: DeleteExemplarRequest):
    """
    Remove exemplars matching text and label.
    Used when an annotation is deleted to keep FAISS in sync.
    """
    retriever = get_retriever()
    removed = retriever.remove_by_text_and_label(request.text, request.label)
    
    return DeleteExemplarResponse(
        removed_count=removed,
        total_exemplars=retriever.count()
    )


@app.post("/search", response_model=SearchResponse)
async def search_exemplars(request: SearchRequest):
    """Search for similar exemplars by text"""
    embeddings = get_embedding_service()
    retriever = get_retriever()
    
    query_embedding = embeddings.embed_single(request.text)
    results = retriever.search(
        query_embedding,
        k=request.k,
        label_filter=request.label_filter
    )
    
    return SearchResponse(
        results=[
            SearchResult(
                id=id,
                score=score,
                text=meta.get("text", ""),
                label=meta.get("label", ""),
                document_id=meta.get("document_id", "")
            )
            for id, score, meta in results
        ]
    )


@app.post("/score", response_model=ScoreResponse)
async def score_annotation(request: ScoreRequest):
    """
    Score an annotation for style similarity.
    
    Computes:
    - Content similarity to similar exemplars
    - Label similarity to label centroid
    - Style similarity to annotator's history
    """
    style_scorer = get_style_scorer()
    embeddings = get_embedding_service()
    retriever = get_retriever()
    
                                                    
    query_embedding = embeddings.embed_single(request.text)
    results = retriever.search(query_embedding, k=5)
    exemplar_embeddings = [
        embeddings.embed_single(f"[{meta.get('label', '')}] {meta.get('text', '')}")
        for _, _, meta in results
    ]
    
    scores = style_scorer.score_suggestion(
        text=request.text,
        label=request.label,
        context=request.context or "",
        rationale=request.rationale or "",
        exemplar_embeddings=exemplar_embeddings,
        annotator_id=request.annotator_id
    )
    
    return ScoreResponse(
        content_similarity=scores["content_similarity"],
        label_similarity=scores["label_similarity"],
        style_similarity=scores["style_similarity"],
        combined_score=scores["combined_score"],
        weights=scores["weights"]
    )


@app.on_event("startup")
async def startup():
    """Initialize services on startup"""
    settings.ensure_directories()
    print(f"\n{'='*50}")
    print(f"ML Service Started")
    print(f"{'='*50}")
    print(f"  Embedding model: {settings.embedding_model}")
    print(f"  LLM provider: {settings.llm_provider}")
    print(f"  Data directory: {settings.data_dir}")
    
                
    try:
        suggester = get_suggester()
        stats = suggester.get_stats()
        print(f"  Exemplars loaded: {stats['retriever']['total_exemplars']}")
        print(f"  Labels tracked: {stats['style_scorer']['labels_tracked']}")
        print(f"  Annotators tracked: {len(stats['style_scorer']['annotators_tracked'])}")
    except Exception as e:
        print(f"  (Stats unavailable: {e})")
    
    print(f"{'='*50}\n")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
