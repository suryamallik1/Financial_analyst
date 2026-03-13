from app.agents.base import BaseAgent
from app.core.resilience import handle_gemini_quota
from app.core.state import PortfolioState, AssetProposal
from app.tools.fundamentals import FundamentalsClient
from datetime import datetime, timedelta
from langchain_core.messages import SystemMessage, HumanMessage

class ValueAnalystAgent(BaseAgent):
    """
    Focuses on Intrinsic Gap analysis.
    Looks for assets where Price < Intrinsic Value based on fundamentals.
    """
    def __init__(self):
        super().__init__()
        self.fundamentals_client = FundamentalsClient()
        self.system_prompt = """
        You are a Value Analyst Agent. 
        Your job is to identify a single intrinsically undervalued asset based on the user's request and fundamentals.
        Output ONLY a JSON object with 'symbol' and 'rationale'.
        """

    @handle_gemini_quota
    async def run(self, state: PortfolioState) -> PortfolioState:
        user_req = state.get('user_request', 'undervalued stocks')
        
        # 1. Ask Gemini to identify a potentially undervalued ticker first
        ident_messages = [
            SystemMessage(content="You are a stock selector. Based on the user request, suggest ONE ticker symbol that is considered 'undervalued' or 'value-oriented'. Output ONLY the ticker symbol."),
            HumanMessage(content=user_req)
        ]
        ticker_res = self.llm.invoke(ident_messages)
        ticker = ticker_res.content.strip().replace('$', '')
        
        # 2. Get real fundamental data (SEC 10-K and News Sentiment)
        print(f"Fetching SEC 10-K for {ticker}...")
        sec_summary = await self.fundamentals_client.get_sec_10k_summary(ticker)
        
        print(f"Fetching news sentiment for {ticker}...")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        news_articles = await self.fundamentals_client.get_news_sentiment(
            ticker, 
            start_date.strftime('%Y-%m-%d'), 
            end_date.strftime('%Y-%m-%d')
        )
        
        # Format news for LLM context (take top 5 headlines/snippets)
        news_context = ""
        for i, art in enumerate(news_articles[:5]):
            news_context += f"- {art.get('title')}: {art.get('description')}\n"
        
        # 3. Generate detailed rationale
        analysis_messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=(
                f"Analyze {ticker} based on these data sources:\n\n"
                f"--- SEC 10-K Analysis ---\n{sec_summary}\n\n"
                f"--- Recent News Snippets ---\n{news_context}\n\n"
                f"User Context: {user_req}"
            ))
        ]
        
        final_res = self.llm.invoke(analysis_messages)
        
        proposal = AssetProposal(
            symbol=ticker,
            rationale=final_res.content,
            strategy_type="intrinsic_gap"
        )
        
        return {"proposals": [proposal], "current_agent": "value_analyst"}
