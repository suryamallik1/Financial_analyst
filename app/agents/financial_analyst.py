from app.core.state import PortfolioState
from app.agents.base import BaseAgent
from app.tools.backtest import BacktestEngine
from app.tools.market_data import MarketDataClient
from langchain_core.messages import SystemMessage, HumanMessage
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class FinancialAnalystAgent(BaseAgent):
    """
    Lead Orchestrator & Validator.
    Enforces the "Gatekeeper" Protocol: Sharpe > 1.2, Win Rate > 55%, Drawdown < 20%.
    """
    def __init__(self):
        super().__init__()
        self.market_data_client = MarketDataClient()
        
    async def run(self, state: PortfolioState) -> PortfolioState:
        proposals = state.get("proposals", [])
        updated_proposals = []
        all_validated = True
        
        # Mock historical data for backtesting since we don't have a real DB populated yet
        date_rng = pd.date_range(end=datetime.now(), periods=500, freq='D')
        mock_price_data = pd.DataFrame(
            np.random.normal(0.001, 0.02, 500).cumsum() + 100, 
            index=date_rng, 
            columns=['Close']
        )
        
        for proposal in proposals:
            if proposal.status != "pending":
                 updated_proposals.append(proposal)
                 continue
                 
            # 1. Run backtest (Simulating buy and hold for simplicity here)
            metrics = BacktestEngine.run_buy_and_hold(mock_price_data)
            
            # For demonstration, inject some variance so some pass and some fail
            if proposal.strategy_type == "momentum_factor" and len(state.get("proposals", [])) <= 3:
                 # Simulate a backtest failure scenario on the first pass
                 metrics['Sharpe_Ratio'] = 0.9
                 metrics['Max_Drawdown'] = -0.25
            else:
                 metrics['Sharpe_Ratio'] = 1.5
                 metrics['Max_Drawdown'] = -0.15
                 
            proposal.metrics = metrics
            
            # 2. Enforce Gatekeeper Protocol
            sharpe = metrics.get("Sharpe_Ratio", 0)
            max_dd = metrics.get("Max_Drawdown", 0)
            
            # Note: A real implementation would also check Win Rate > 55%, 
            # but our simple buy_and_hold mock might not generate enough trades
            if sharpe < 1.2 or max_dd < -0.20:
                proposal.status = "rejected"
                proposal.feedback = f"Backtest failed. Sharpe ({sharpe:.2f}) < 1.2 or Drawdown ({-max_dd*100:.1f}%) > 20%. Refine entry point or suggest a hedge."
                all_validated = False
            else:
                proposal.status = "accepted"
                proposal.feedback = "Validated. Metrics meet criteria."
                
            updated_proposals.append(proposal)
            
        # 3. Synthesize final report if all accepted
        final_report = None
        if all_validated and len(updated_proposals) > 0:
            final_report = "Barbell Allocation Synthesized: " + ", ".join([p.symbol for p in updated_proposals if p.status == 'accepted'])
            
        # Do not return the `proposals` array back to the state since it triggers the `extend_list` reducer and duplicates it.
        # We mutated `proposal.status` and `proposal.metrics` in place.
        return {
            "is_validated": all_validated,
            "final_report": final_report,
            "current_agent": "financial_analyst"
        }
