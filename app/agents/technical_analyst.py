from app.core.state import PortfolioState, AssetProposal
from app.agents.base import BaseAgent
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

    async def run(self, state: PortfolioState) -> PortfolioState:
        # In a real app, calculate indicators (RSI, MACD, etc.) to find a signal
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"Suggest a momentum play for: {state.get('user_request', 'general portfolio')}")
        ]
        
        # Hardcoding a realistic suggestion for demo purposes
        proposal = AssetProposal(
            symbol="NVDA", # Example
            rationale="Golden cross approaching, RSI at 60 indicating sustained upward momentum without being overbought.",
            strategy_type="momentum_factor"
        )
        
        return {"proposals": [proposal], "current_agent": "technical_analyst"}
