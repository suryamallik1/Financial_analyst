from app.core.state import PortfolioState, AssetProposal
from app.agents.base import BaseAgent
from app.tools.macro_data import MacroDataClient
from langchain_core.messages import SystemMessage, HumanMessage

class RiskComplianceAgent(BaseAgent):
    """
    Focuses on Macro-Correlations & Capital Preservation.
    Looks at Bond Yield inversions, VIX, and suggests broad hedges.
    """
    def __init__(self):
        super().__init__()
        self.macro_data_client = MacroDataClient()
        self.system_prompt = """
        You are a Risk & Compliance Agent. 
        Your job is to suggest a defensive asset or hedge based on macroeconomic conditions.
        Output ONLY a JSON object with 'symbol' (e.g., TLT for bonds, GLD for gold) and 'rationale'.
        """

    async def run(self, state: PortfolioState) -> PortfolioState:
        # In a real app, fetch yield curve and VIX
        
        # Hardcoding a realistic suggestion for demo purposes
        proposal = AssetProposal(
            symbol="TLT", # Example hedge
            rationale="Yield curve remains inverted; adding long-duration treasuries as a macro hedge against potential equity drawdowns.",
            strategy_type="macro_hedge"
        )
        
        return {"proposals": [proposal], "current_agent": "risk_compliance"}
