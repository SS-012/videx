"""
Agentic Chat Service - OpenAI with Tool Calling for Annotation
"""

from __future__ import annotations

import json
from typing import List, Dict, Any, Optional
from openai import OpenAI

from backend.app.config import settings
from backend.app.services.local_storage import get_storage
from backend.app.services.ml_client import get_ml_client


                                            

ANNOTATION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "suggest_annotations",
            "description": "Use AI to analyze the document and suggest entities to annotate. Call this when the user asks to find entities, suggest annotations, or analyze the document for named entities.",
            "parameters": {
                "type": "object",
                "properties": {
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of specific labels to look for (e.g., ['ORG', 'PERSON']). If not provided, searches for all entity types."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_annotation",
            "description": "Create a new annotation on the document. Use this when the user explicitly asks to annotate a specific piece of text with a specific label.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The exact text to annotate (must exist in the document)"
                    },
                    "label": {
                        "type": "string",
                        "description": "The label for the annotation (e.g., ORG, PERSON, LOCATION, DATE, ANIMAL, or any custom label the user specifies)"
                    },
                    "rationale": {
                        "type": "string",
                        "description": "Brief explanation of why this text should have this label (e.g., 'Company name', 'Geographic location', 'Superlative adjective')"
                    }
                },
                "required": ["text", "label", "rationale"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_annotations",
            "description": "List all current annotations on the document. Use this when the user asks what has been annotated, wants to see current annotations, or asks about annotation progress.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_annotation",
            "description": "Delete an existing annotation. Use this when the user asks to remove or delete an annotation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text of the annotation to delete"
                    }
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "batch_annotate_all",
            "description": "Automatically annotate ALL documents in the sidebar. Use this when the user asks to 'annotate all documents', 'go through all files', 'batch annotate', or similar requests to process multiple documents at once.",
            "parameters": {
                "type": "object",
                "properties": {
                    "auto_accept": {
                        "type": "boolean",
                        "description": "If true, automatically accept all suggestions. If false, just report what would be annotated."
                    }
                },
                "required": ["auto_accept"]
            }
        }
    }
]


SYSTEM_PROMPT = """You are VIDEX, an advanced annotation intelligence system. Think JARVIS meets data science.

## Personality
- Precise, efficient, no fluff
- Dry wit when appropriate - you're smart and you know it
- Confident but not arrogant
- Speak in clean, clipped sentences
- Occasionally sardonic observations are welcome
- Never say "I'd be happy to help" or similar corporate pleasantries
- Skip the preamble - get to the point

## Your Capabilities
You have tools at your disposal:
- **suggest_annotations** - Scan and identify entities worth annotating
- **create_annotation** - Tag specific text with a label
- **list_annotations** - Display current annotations
- **delete_annotation** - Remove an annotation
- **batch_annotate_all** - Process ALL documents at once. Use when asked to "annotate all docs", "go through everything", etc.

## Entity Types
Standard labels: ORG, PERSON, LOCATION, DATE, OTHER
Custom labels: Users can define their own. Use whatever they specify.

## Behavior
- When asked to find/suggest entities, use your tools immediately. Don't ask permission.
- When the document is clean, say so. Don't manufacture entities that aren't there.
- If you spot something obvious the user missed, point it out.
- Keep responses tight. This isn't a thesis defense.
- IMPORTANT: If there are no entities to annotate, just say so clearly. NEVER say "service unavailable" or imply technical issues when you simply found nothing.
- Think creatively about labels - if user has custom labels like DAY, NATURE, etc., consider if those apply.
- If you initially miss something and user pushes back, reconsider. You're good, but not infallible.

## Rationale Handling
When creating annotations, you must provide a rationale (brief explanation of why this label applies).
- If the user explains their reasoning (e.g., "tag X as Y because it's a Z"), distill their reasoning into a concise rationale. Keep the core meaning, trim the fluff.
- If no reasoning is given, generate a brief rationale yourself based on context and entity type.
- Keep rationales short: 3-8 words typically. Examples: "Company name", "Geographic location", "Superlative adjective", "Day of the week".

## Response Style Examples
- "Three entities detected. Apple (ORG), Cook (PERSON), Cupertino (LOCATION). Shall I tag them?"
- "Nothing to tag here. Document's entity-free."
- "Done. Tagged 'Microsoft' as ORG."
- "That text doesn't exist in the document. Check your spelling."
- "Already annotated. You're covered."
- "Scanned again. Still nothing. The text is just... text."
- "My bad. Missed 'Monday' - that's a DAY. Want me to tag it?"

## What NOT to say
- Never say "service unavailable" when you just found no entities
- Never imply technical problems when there's simply nothing to annotate
- Never blame tools or systems for your analysis results

Be the annotation system users didn't know they needed."""


class ChatAgent:
    """Agentic chat service with tool calling for annotation"""
    
    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.storage = get_storage()
    
    async def chat(
        self,
        message: str,
        document_id: Optional[str] = None,
        document_content: Optional[str] = None,
        labels: Optional[List[str]] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Process a chat message with tool calling support.
        
        Returns:
            Dict with:
            - response: The assistant's text response
            - tool_results: List of tool call results (if any)
            - annotations_created: List of annotations created (if any)
            - suggestions: List of annotation suggestions (if any)
        """
                        
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
                                         
        if labels:
            labels_str = ", ".join(labels)
            messages[0]["content"] += f"\n\n## Available Labels\nThe user has configured these labels: {labels_str}"
        
                              
        if document_content:
            context_msg = f"\n\n## Current Document\n```\n{document_content[:4000]}\n```"
            if document_id:
                                          
                annotations = self.storage.get_annotations(document_id)
                if annotations:
                    ann_summary = "\n".join([
                        f"- [{a['label']}] \"{a.get('text', 'N/A')}\"" 
                        for a in annotations[:20]
                    ])
                    context_msg += f"\n\n## Existing Annotations ({len(annotations)} total)\n{ann_summary}"
            
            messages[0]["content"] += context_msg
        
                     
        if history:
            for msg in history[-8:]:                   
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
        
                          
        messages.append({"role": "user", "content": message})
        
                                
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=ANNOTATION_TOOLS,
            tool_choice="auto",
            temperature=0.7,
            max_tokens=1000
        )
        
        assistant_message = response.choices[0].message
        
                                   
        tool_results = []
        annotations_created = []
        suggestions = []
        
        if assistant_message.tool_calls:
                                    
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                result = await self._execute_tool(
                    tool_name, 
                    tool_args, 
                    document_id, 
                    document_content,
                    labels
                )
                
                tool_results.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "result": result
                })
                
                                           
                if tool_name == "create_annotation" and result.get("success"):
                    annotations_created.append(result.get("annotation"))
                
                                   
                if tool_name == "suggest_annotations":
                    suggestions = result.get("suggestions", [])
            
                                                     
            messages.append(assistant_message)
            
            for i, tool_call in enumerate(assistant_message.tool_calls):
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_results[i]["result"])
                })
            
                                
            final_response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            response_text = final_response.choices[0].message.content or ""
        else:
            response_text = assistant_message.content or ""
        
        return {
            "response": response_text,
            "tool_results": tool_results,
            "annotations_created": annotations_created,
            "suggestions": suggestions
        }
    
    async def _execute_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        document_id: Optional[str],
        document_content: Optional[str],
        available_labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Execute a tool and return the result"""
        
        if tool_name == "suggest_annotations":
                                                                                            
            tool_labels = args.get("labels") or available_labels
            return await self._tool_suggest(document_id, document_content, tool_labels)
        
        elif tool_name == "create_annotation":
            return await self._tool_create_annotation(
                document_id,
                document_content,
                args.get("text", ""),
                args.get("label", "OTHER"),
                args.get("rationale", "")
            )
        
        elif tool_name == "list_annotations":
            return self._tool_list_annotations(document_id)
        
        elif tool_name == "delete_annotation":
            return self._tool_delete_annotation(document_id, args.get("text", ""))
        
        elif tool_name == "batch_annotate_all":
            return await self._tool_batch_annotate_all(
                args.get("auto_accept", False),
                available_labels
            )
        
        return {"error": f"Unknown tool: {tool_name}"}
    
    async def _tool_suggest(
        self,
        document_id: Optional[str],
        document_content: Optional[str],
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get AI suggestions for annotations"""
        if not document_content:
            return {"error": "No document loaded", "suggestions": []}
        
        try:
            ml_client = get_ml_client()
            if not await ml_client.health():
                return {"error": "ML service not available", "suggestions": []}
            
                                                                   
            suggest_labels = labels if labels else ["ORG", "PERSON", "LOCATION", "DATE", "OTHER"]
            
            result = await ml_client.suggest(
                text=document_content,
                task="ner",
                labels=suggest_labels,
                top_k=5
            )
            
            suggestions = result.get("suggestions", [])
            return {
                "success": True,
                "count": len(suggestions),
                "suggestions": [
                    {
                        "text": s.get("text"),
                        "label": s.get("label"),
                        "confidence": s.get("confidence", 0.7)
                    }
                    for s in suggestions
                ]
            }
        except Exception as e:
            return {"error": str(e), "suggestions": []}
    
    async def _tool_create_annotation(
        self,
        document_id: Optional[str],
        document_content: Optional[str],
        text: str,
        label: str,
        rationale: str = ""
    ) -> Dict[str, Any]:
        """Create an annotation on the document and add it as an exemplar for future learning"""
        if not document_id:
            return {"error": "No document selected", "success": False}
        
        if not document_content:
            return {"error": "No document content", "success": False}
        
                                       
        start_idx = document_content.find(text)
        if start_idx == -1:
            return {
                "error": f"Text '{text}' not found in document",
                "success": False
            }
        
        end_idx = start_idx + len(text)
        
                               
        annotation = self.storage.save_annotation(document_id, {
            "label": label,
            "span_start": start_idx,
            "span_end": end_idx,
            "text": text,
            "confidence": 1.0,
            "source": "chat"
        })
        
                                                                
        try:
            ml_client = get_ml_client()
            health_ok = await ml_client.health()
            print(f"[EXEMPLAR] Health check: {health_ok}")
            
            if health_ok:
                                                               
                context_start = max(0, start_idx - 100)
                context_end = min(len(document_content), end_idx + 100)
                context = document_content[context_start:context_end]
                
                print(f"[EXEMPLAR] Adding: text='{text}', label='{label}', rationale='{rationale}', doc={document_id}")
                result = await ml_client.add_exemplar(
                    document_id=document_id,
                    text=text,
                    label=label,
                    span_start=start_idx,
                    span_end=end_idx,
                    context=context,
                    rationale=rationale
                )
                print(f"[EXEMPLAR] Success: {result}")
            else:
                print("[EXEMPLAR] Health check failed, skipping")
        except Exception as e:
            print(f"[EXEMPLAR] Failed to add exemplar: {e}")
            import traceback
            traceback.print_exc()
                                                                  
        
        return {
            "success": True,
            "annotation": {
                "id": annotation.get("id"),
                "text": text,
                "label": label,
                "span_start": start_idx,
                "span_end": end_idx
            }
        }
    
    def _tool_list_annotations(self, document_id: Optional[str]) -> Dict[str, Any]:
        """List all annotations on the document"""
        if not document_id:
            return {"error": "No document selected", "annotations": []}
        
        annotations = self.storage.get_annotations(document_id)
        
        return {
            "count": len(annotations),
            "annotations": [
                {
                    "id": a.get("id"),
                    "text": a.get("text"),
                    "label": a.get("label"),
                    "source": a.get("source", "unknown")
                }
                for a in annotations
            ]
        }
    
    def _tool_delete_annotation(
        self,
        document_id: Optional[str],
        text: str
    ) -> Dict[str, Any]:
        """Delete an annotation by text"""
        if not document_id:
            return {"error": "No document selected", "success": False}
        
        annotations = self.storage.get_annotations(document_id)
        
                                 
        for ann in annotations:
            if ann.get("text") == text:
                self.storage.delete_annotation(document_id, ann["id"])
                return {
                    "success": True,
                    "deleted": {"text": text, "label": ann.get("label")}
                }
        
        return {"error": f"No annotation found with text '{text}'", "success": False}
    
    async def _tool_batch_annotate_all(
        self,
        auto_accept: bool = False,
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Batch annotate all documents in the system"""
        
                           
        documents = self.storage.list_documents()
        
        if not documents:
            return {"error": "No documents found", "success": False}
        
        results = {
            "documents_processed": 0,
            "total_documents": len(documents),
            "annotations_created": 0,
            "suggestions_found": 0,
            "details": []
        }
        
        ml_client = get_ml_client()
        if not await ml_client.health():
            return {"error": "ML service not available", "success": False}
        
        suggest_labels = labels if labels else ["ORG", "PERSON", "LOCATION", "DATE", "OTHER"]
        
        for doc in documents:
            doc_id = doc.get("id")
            doc_name = doc.get("name", doc_id)
            
                                  
            content = self.storage.get_document_content(doc_id)
            if not content:
                continue
            
            try:
                                                   
                result = await ml_client.suggest(
                    text=content,
                    task="ner",
                    labels=suggest_labels,
                    top_k=5
                )
                
                suggestions = result.get("suggestions", [])
                doc_annotations = []
                
                if auto_accept and suggestions:
                                                                  
                    existing_annotations = self.storage.get_annotations(doc_id)
                    existing_set = {(a.get("text"), a.get("label")) for a in existing_annotations}
                    
                                                                    
                                                          
                    for suggestion in suggestions:
                        text = suggestion.get("text", "")
                        label = suggestion.get("label", "")
                        
                        if not text or not label:
                            continue
                        
                                                           
                        if (text, label) in existing_set:
                            continue
                        
                                               
                        start_idx = content.find(text)
                        if start_idx == -1:
                            continue
                        
                        end_idx = start_idx + len(text)
                        
                                                                                        
                        annotation = self.storage.save_annotation(doc_id, {
                            "label": label,
                            "span_start": start_idx,
                            "span_end": end_idx,
                            "text": text,
                            "confidence": suggestion.get("confidence", 0.8),
                            "source": "pending_batch"                                 
                        })
                        
                                                                                  
                        
                        doc_annotations.append({"text": text, "label": label})
                        results["annotations_created"] += 1
                
                results["suggestions_found"] += len(suggestions)
                results["documents_processed"] += 1
                results["details"].append({
                    "document": doc_name,
                    "suggestions": len(suggestions),
                    "annotations_created": len(doc_annotations) if auto_accept else 0,
                    "items": doc_annotations if auto_accept else [
                        {"text": s.get("text"), "label": s.get("label")} 
                        for s in suggestions
                    ]
                })
                
            except Exception as e:
                results["details"].append({
                    "document": doc_name,
                    "error": str(e)
                })
        
        results["success"] = True
        return results


           
_chat_agent: Optional[ChatAgent] = None


def get_chat_agent() -> ChatAgent:
    global _chat_agent
    if _chat_agent is None:
        _chat_agent = ChatAgent()
    return _chat_agent
