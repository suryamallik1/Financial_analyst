from app.agents.base import BaseAgent
from app.core.resilience import handle_gemini_quota
from app.core.state import PortfolioState, AssetProposal
from app.tools.market_data import MarketDataClient
from app.tools.search import SearchClient
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.callbacks.manager import adispatch_custom_event

class TechnicalAnalystAgent(BaseAgent):
    """
    Focuses on Momentum Factor strategy.
    Looks for assets based on moving average crossovers and RSI levels.
    """
    def __init__(self):
        super().__init__()
        self.market_data_client = MarketDataClient()
        self.search_client = SearchClient()
        self.system_prompt = """
        You are a Technical Analyst Agent. 
        Your job is to identify an asset with strong momentum based on the user's request.
        Output ONLY a JSON object with 'symbol', 'rationale', 'entry_signal' (e.g. SMA50 > SMA200), and 'exit_signal'.
        """

    @handle_gemini_quota
    async def run(self, state: PortfolioState) -> PortfolioState:
        user_req = state.get('user_request', 'momentum stocks')
        
        # 1. Search for momentum candidates based on user request
        print(f"Searching for momentum candidates for: {user_req}")
        search_results = await self.search_client.search_candidates(f"best momentum stocks and breakout trading ideas for: {user_req}")
        search_context = "\n".join([f"- {res.get('title')}: {res.get('snippet')}" for res in search_results[:5]])

        # 2. Ask Gemini to identify a momentum candidate based on search context and Lead Analyst's plan
        ident_messages = [
            SystemMessage(content=(
                "You are a Technical Strategy Selector. Suggest ONE ticker symbol showing strong momentum characteristics "
                "that is STRICTLY RELEVANT to the User Request and the Lead Analyst's Execution Plan. Output ONLY the ticker symbol."
            )),
            HumanMessage(content=(
                f"User Request: {user_req}\n\n"
                f"Lead Analyst Plan: {state.get('analysis_plan', 'Focus on momentum-oriented assets.')}\n\n"
                f"Recent Technical Context:\n{search_context}"
            ))
        ]
        ticker_res = await self.llm.ainvoke(ident_messages)
        content = ticker_res.content
        if isinstance(content, list):
            content = " ".join([p.get("text", "") if isinstance(p, dict) else str(p) for p in content])
        ticker = str(content).strip().replace('$', '').split()[0]
        
        # 2. Get real technical data (RSI) from Alpha Vantage
        print(f"Fetching Alpha Vantage technicals for {ticker}...")
        await adispatch_custom_event("tool_call", {"tool": "AlphaVantage_Technicals", "input": ticker})
        try:
            rsi_data = await self.market_data_client.get_alpha_vantage_indicators(ticker, "RSI")
            # Alpha Vantage returns complex nested JSON, we'll pass it as a string for context
            tech_context = str(rsi_data).split('Technical Analysis')[-1][:2000] # Take a relevant chunk
        except Exception as e:
            tech_context = f"Error fetching technicals: {e}"
        
        # 3. Generate detailed rationale
        analysis_messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"Provide a technical analysis rationale for {ticker} based on this technical data: {tech_context}\n\nUser context: {user_req}")
        ]
        
        final_res = await self.llm.ainvoke(analysis_messages)
        parsed_res = self.parse_llm_json(final_res.content)
        
        proposal = AssetProposal(
            symbol=ticker,
            rationale=parsed_res.get("rationale", str(final_res.content)),
            strategy_type="momentum_factor"
        )
        
        return {"proposals": [proposal], "current_agent": "technical_analyst"}
