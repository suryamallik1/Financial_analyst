from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings
from app.core.resilience import handle_gemini_quota

def get_llm():
    """Provides a configured LLM instance with quota handling."""
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash", 
        temperature=0.2,
        google_api_key=settings.GOOGLE_API_KEY
    )
    # Note: agents use .invoke() or .ainvoke()
    # To handle 429s globally, we'd ideally wrap the .invoke/ainvoke methods
    return llm
    
class BaseAgent:
    """Base class for specialist agents."""
    def __init__(self):
        self.llm = get_llm()
