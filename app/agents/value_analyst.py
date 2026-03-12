from app.core.state import PortfolioState, AssetProposal
from app.agents.base import BaseAgent
from app.tools.fundamentals import FundamentalsClient
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

    async def run(self, state: PortfolioState) -> PortfolioState:
        # 1. Look at user request
        # 2. In a real app, query fundamental data to find a stock
        # For this prototype, we'll ask the LLM to pick one based on prompt
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"Suggest an undervalued stock for: {state.get('user_request', 'general portfolio')}")
        ]
        
        # Simplified for prototype: normally we'd parse JSON from LLM
        # Hardcoding a realistic suggestion for demo purposes
        proposal = AssetProposal(
            symbol="AAPL", # Example
            rationale="Strong balance sheet, consistent cash flow generation, temporary market undervaluation due to macro noise.",
            strategy_type="intrinsic_gap"
        )
        
        return {"proposals": [proposal], "current_agent": "value_analyst"}
