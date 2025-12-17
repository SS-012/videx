from __future__ import annotations

import json
import re
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

from ml_service.config import settings


class LLMClient(ABC):
    """Abstract base class for LLM clients"""
    
    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a completion"""
        pass


class StubLLMClient(LLMClient):
    """Stub client that returns mock responses for testing"""
    
    def complete(self, system_prompt: str, user_prompt: str) -> str:
                                       
        text_match = re.search(r'Text to annotate:\s*"([^"]+)"', user_prompt)
        if not text_match:
            text_match = re.search(r'Text to classify:\s*"([^"]+)"', user_prompt)
        
        if not text_match:
            return "[]"
        
        text = text_match.group(1)
        
                                                              
        entities = []
        words = text.split()
        pos = 0
        
        for word in words:
                                            
            idx = text.find(word, pos)
            if idx == -1:
                pos += len(word) + 1
                continue
            
                                                                     
            if word[0].isupper() and idx > 0 and text[idx-1] != '.':
                clean_word = word.rstrip('.,!?;:')
                entities.append({
                    "text": clean_word,
                    "label": "ORG",                  
                    "start": idx,
                    "end": idx + len(clean_word)
                })
            
            pos = idx + len(word)
        
        return json.dumps(entities)


class OpenAIClient(LLMClient):
    """OpenAI API client"""
    
    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set")
        
        from openai import OpenAI
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=90.0                                   
        )
        self.model = settings.openai_model
    
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        return response.choices[0].message.content or ""


def get_llm_client() -> LLMClient:
    """Factory function to get the appropriate LLM client"""
    if settings.llm_provider == "openai" and settings.openai_api_key:
        return OpenAIClient()
    return StubLLMClient()


def parse_json_response(response: str) -> Any:
    """Parse JSON from LLM response, handling markdown code blocks"""
                                                   
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
    if json_match:
        response = json_match.group(1)
    
                           
    response = response.strip()
    
    try:
        return json.loads(response)
    except json.JSONDecodeError:
                                             
        array_match = re.search(r'\[[\s\S]*\]', response)
        if array_match:
            try:
                return json.loads(array_match.group())
            except:
                pass
        
        obj_match = re.search(r'\{[\s\S]*\}', response)
        if obj_match:
            try:
                return json.loads(obj_match.group())
            except:
                pass
        
        return None

