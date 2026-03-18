from app.agents.base import BaseAgent
from app.core.resilience import handle_gemini_quota
from app.core.state import PortfolioState, AssetProposal
from app.tools.fundamentals import FundamentalsClient
from app.tools.search import SearchClient
from datetime import datetime, timedelta
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.callbacks.manager import adispatch_custom_event

class ValueAnalystAgent(BaseAgent):
    """
    Focuses on Intrinsic Gap analysis.
    Looks for assets where Price < Intrinsic Value based on fundamentals.
    """
    def __init__(self):
        super().__init__()
        self.fundamentals_client = FundamentalsClient()
        self.search_client = SearchClient()
        self.system_prompt = """
        You are a Value Analyst Agent. 
        Your job is to identify a single intrinsically undervalued asset based on the user's request and fundamentals.
        Output ONLY a JSON object with 'symbol' and 'rationale'.
        """

    @handle_gemini_quota
    async def run(self, state: PortfolioState) -> PortfolioState:
        user_req = state.get('user_request', 'undervalued stocks')
        
        # 1. Search for candidates based on user request
        print(f"Searching for value candidates for: {user_req}")
        search_results = await self.search_client.search_candidates(f"best undervalued stocks and value investment ideas for: {user_req}")
        search_context = "\n".join([f"- {res.get('title')}: {res.get('snippet')}" for res in search_results[:5]])
        
        # 2. Ask Gemini to identify a potentially undervalued ticker based on search context and Lead Analyst's plan
        ident_messages = [
            SystemMessage(content=(
                "You are an expert stock selector. Based on the User Request, the Lead Analyst's Execution Plan, "
                "and recent market news provided, suggest ONE ticker symbol that is 'undervalued' or 'value-oriented' "
                "and STRICTLY RELEVANT to the objective. Output ONLY the ticker symbol."
            )),
            HumanMessage(content=(
                f"User Request: {user_req}\n\n"
                f"Lead Analyst Plan: {state.get('analysis_plan', 'Focus on value-oriented assets.')}\n\n"
                f"Recent Market Context:\n{search_context}"
            ))
        ]
        ticker_res = await self.llm.ainvoke(ident_messages)
        content = ticker_res.content
        if isinstance(content, list):
            # Extract text from parts if it's a list
            content = " ".join([p.get("text", "") if isinstance(p, dict) else str(p) for p in content])
        ticker = str(content).strip().replace('$', '').split()[0] # Take first word (ticker)
        
        # 2. Get real fundamental data (SEC 10-K and News Sentiment)
        print(f"Fetching SEC 10-K for {ticker}...")
        await adispatch_custom_event("tool_call", {"tool": "SEC_10K_Client", "input": ticker})
        sec_summary = await self.fundamentals_client.get_sec_10k_summary(ticker)
        
        print(f"Fetching news sentiment for {ticker}...")
        await adispatch_custom_event("tool_call", {"tool": "News_API_Client", "input": ticker})
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
        
        final_res = await self.llm.ainvoke(analysis_messages)
        parsed_res = self.parse_llm_json(final_res.content)
        
        proposal = AssetProposal(
            symbol=ticker,
            rationale=parsed_res.get("rationale", str(final_res.content)),
            strategy_type="intrinsic_gap"
        )
        
        return {"proposals": [proposal], "current_agent": "value_analyst"}
