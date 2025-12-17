"""
Chat Router - Agentic Annotation Assistant with Tool Calling
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Any

from backend.app.config import settings

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class AnnotationResult(BaseModel):
    id: Optional[str] = None
    text: str
    label: str
    span_start: Optional[int] = None
    span_end: Optional[int] = None


class SuggestionResult(BaseModel):
    text: Optional[str] = None
    label: str
    confidence: float


class ToolResult(BaseModel):
    tool: str
    args: dict
    result: dict


class ChatRequest(BaseModel):
    message: str
    document_id: Optional[str] = None
    document_context: Optional[str] = None
    labels: Optional[List[str]] = None
    history: Optional[List[ChatMessage]] = None


class ChatResponse(BaseModel):
    response: str
    tool_results: Optional[List[ToolResult]] = None
    annotations_created: Optional[List[AnnotationResult]] = None
    suggestions: Optional[List[SuggestionResult]] = None
    agent_available: bool = True


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the agentic annotation assistant.
    
    The assistant can:
    - Suggest annotations using AI
    - Create annotations on the document
    - List existing annotations
    - Delete annotations
    - Answer questions about annotation
    """
    
                                         
    if settings.openai_api_key:
        try:
            from backend.app.services.chat_agent import get_chat_agent
            
            agent = get_chat_agent()
            result = await agent.chat(
                message=request.message,
                document_id=request.document_id,
                document_content=request.document_context,
                labels=request.labels,
                history=[m.model_dump() for m in request.history] if request.history else None
            )
            
            return ChatResponse(
                response=result["response"],
                tool_results=[ToolResult(**tr) for tr in result.get("tool_results", [])],
                annotations_created=[
                    AnnotationResult(**ann) 
                    for ann in result.get("annotations_created", [])
                ] if result.get("annotations_created") else None,
                suggestions=[
                    SuggestionResult(**s) 
                    for s in result.get("suggestions", [])
                ] if result.get("suggestions") else None,
                agent_available=True
            )
        except Exception as e:
            print(f"Chat agent error: {e}")
                                      
    
                                                       
    return ChatResponse(
        response=generate_fallback_response(request.message, request.document_context),
        agent_available=False
    )


def generate_fallback_response(message: str, context: str = None) -> str:
    """Generate a helpful response when OpenAI is not available"""
    message_lower = message.lower()
    
    if "suggest" in message_lower or "annotate" in message_lower or "find" in message_lower:
        return """I'd love to help suggest annotations, but I need an OpenAI API key to use my full capabilities.

**To enable the AI assistant:**
1. Add `OPENAI_API_KEY=your-key` to your `.env` file
2. Restart the backend server

In the meantime, you can:
- Use the **AI Suggest** button in the toolbar
- Manually select text and choose a label"""
    
    if "org" in message_lower or "person" in message_lower or "location" in message_lower or "date" in message_lower:
        labels = {
            "org": "**ORG**: Organizations, companies, institutions (Apple, FBI, Harvard)",
            "person": "**PERSON**: Individual names (Elon Musk, Dr. Smith)",
            "location": "**LOCATION**: Places, cities, countries (New York, France)",
            "date": "**DATE**: Dates and time expressions (January 2024, Q4)"
        }
        for key, desc in labels.items():
            if key in message_lower:
                return desc
    
    return """I'm your annotation assistant! I can help with:

• **Suggest annotations** - "Find entities in this document"
• **Create annotations** - "Annotate 'Apple Inc.' as ORG"
• **List annotations** - "What have I annotated?"
• **Delete annotations** - "Remove the annotation for 'Apple'"

*Note: Full AI capabilities require an OpenAI API key.*"""
