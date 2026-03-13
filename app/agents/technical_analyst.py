from app.agents.base import BaseAgent
from app.core.resilience import handle_gemini_quota
from app.core.state import PortfolioState, AssetProposal
from app.tools.market_data import MarketDataClient
from langchain_core.messages import SystemMessage, HumanMessage

class TechnicalAnalystAgent(BaseAgent):
    """
    Focuses on Momentum Factor strategy.
    Looks for assets based on moving average crossovers and RSI levels.
    """
    def __init__(self):
        super().__init__()
        self.market_data_client = MarketDataClient()
        self.system_prompt = """
        You are a Technical Analyst Agent. 
        Your job is to identify an asset with strong momentum based on the user's request.
        Output ONLY a JSON object with 'symbol', 'rationale', 'entry_signal' (e.g. SMA50 > SMA200), and 'exit_signal'.
        """

    @handle_gemini_quota
    async def run(self, state: PortfolioState) -> PortfolioState:
        user_req = state.get('user_request', 'momentum stocks')
        
        # 1. Ask Gemini to identify a momentum candidate
        ident_messages = [
            SystemMessage(content="You are a Technical Strategy Selector. Suggest ONE ticker symbol showing strong momentum characteristics (e.g., trend following, breakouts). Output ONLY the ticker symbol."),
            HumanMessage(content=user_req)
        ]
        ticker_res = self.llm.invoke(ident_messages)
        ticker = ticker_res.content.strip().replace('$', '')
        
        # 2. Get real technical data (RSI) from Alpha Vantage
        print(f"Fetching Alpha Vantage technicals for {ticker}...")
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
        
        final_res = self.llm.invoke(analysis_messages)
        
        proposal = AssetProposal(
            symbol=ticker,
            rationale=final_res.content,
            strategy_type="momentum_factor"
        )
        
        return {"proposals": [proposal], "current_agent": "technical_analyst"}
