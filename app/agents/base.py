from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings

def get_llm():
    """Provides a configured LLM instance."""
    return ChatGoogleGenerativeAI(
        model="gemini-3.1-pro",  # Assuming standard gemini model for general uses
        temperature=0.2,
        google_api_key=settings.GOOGLE_API_KEY
    )
    
class BaseAgent:
    """Base class for specialist agents."""
    def __init__(self):
        self.llm = get_llm()
