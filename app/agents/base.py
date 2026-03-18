from typing import Any, Dict, List
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings
from app.core.resilience import handle_gemini_quota

import json
import re

def get_llm():
    """Provides a configured LLM instance with quota handling."""
    llm = ChatGoogleGenerativeAI(
        model="gemini-3-flash-preview", 
        temperature=0.2,
        google_api_key=settings.GOOGLE_API_KEY
    )
    return llm
    
class BaseAgent:
    """Base class for specialist agents."""
    def __init__(self):
        self.llm = get_llm()

    def parse_llm_json(self, response_content: Any) -> Dict[str, Any]:
        """Robustly extracts and parses JSON from LLM response."""
        text = self.extract_llm_text(response_content)
        # Try to find JSON block
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # If no block or parsing fails, return text as rationale
        return {"rationale": text}

    def extract_llm_text(self, content: Any) -> str:
        """Extracts text from various LangChain/Gemini response formats."""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return " ".join([p.get("text", "") if isinstance(p, dict) else str(p) for p in content])
        return str(content)
