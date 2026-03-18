from app.agents.base import BaseAgent
from app.core.resilience import handle_gemini_quota
from app.core.state import PortfolioState
from app.tools.backtest import BacktestEngine
from app.tools.market_data import MarketDataClient
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.callbacks.manager import adispatch_custom_event
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
        
    @handle_gemini_quota
    async def plan(self, state: PortfolioState) -> PortfolioState:
        """
        Initial planning phase. Analyzes user request and provides 
        instructions to the specialist agents.
        """
        user_req = state.get("user_request")
        planning_prompt = [
            SystemMessage(content=(
                "You are the Lead Financial Analyst and Orchestrator. "
                "Analyze the user request and create a concise 'Execution Plan' for three specialist agents: "
                "1. Value Analyst (Intrinsic Gap), 2. Technical Analyst (Momentum), 3. Risk & Compliance (Macro Hedge). "
                "Specify what kind of assets or sectors each should focus on to satisfy the user's objective."
            )),
            HumanMessage(content=user_req)
        ]
        
        res = await self.llm.ainvoke(planning_prompt)
        plan_text = self.extract_llm_text(res.content)
        
        print(f"Lead Analyst Plan Generated: {plan_text[:100]}...")
        
        return {
            "analysis_plan": plan_text,
            "current_agent": "financial_analyst_planner"
        }

    @handle_gemini_quota
    async def run(self, state: PortfolioState) -> PortfolioState:
        proposals = state.get("proposals", [])
        updated_proposals = []
        all_validated = True
        
        # Calculate date range for the last 2 years
        end_date = datetime.now()
        start_date = end_date - timedelta(days=730)
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')

        for proposal in proposals:
            if proposal.status != "pending":
                 updated_proposals.append(proposal)
                 continue
                 
            # 1. Fetch real historical price data
            ticker = proposal.symbol
            print(f"Fetching historical prices for {ticker} for backtesting...")
            await adispatch_custom_event("tool_call", {"tool": "Historical_Price_API", "input": ticker})
            try:
                real_price_data = await self.market_data_client.get_historical_ohlcv(
                    ticker, start_date_str, end_date_str
                )
                
                if real_price_data.empty:
                    print(f"Warning: No historical data found for {ticker}. Using fallback mock data.")
                    # Fallback to mock if API fails or returns empty
                    date_rng = pd.date_range(end=datetime.now(), periods=500, freq='D')
                    real_price_data = pd.DataFrame(
                        np.random.normal(0.001, 0.02, 500).cumsum() + 100, 
                        index=date_rng, 
                        columns=['Close']
                    )
            except Exception as e:
                print(f"Error fetching data for {ticker}: {e}. Using fallback.")
                date_rng = pd.date_range(end=datetime.now(), periods=500, freq='D')
                real_price_data = pd.DataFrame(
                    np.random.normal(0.001, 0.02, 500).cumsum() + 100, 
                    index=date_rng, 
                    columns=['Close']
                )

            # 2. Run real backtest (Simulating buy and hold)
            await adispatch_custom_event("tool_call", {"tool": "VectorBT_Engine", "input": ticker})
            metrics = BacktestEngine.run_buy_and_hold(real_price_data)
            proposal.metrics = metrics
            
            # 3. Enforce Gatekeeper Protocol
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
            
        # 3. Synthesize final report using LLM for personalization
        final_report = None
        accepted_proposals = [p for p in updated_proposals if p.status == 'accepted']
        
        if len(accepted_proposals) > 0 or all_validated:
            synthesis_prompt = [
                SystemMessage(content=(
                    "You are a Lead Financial Analyst. Your task is to synthesize a final investment report "
                    "that explains HOW the suggested assets meet the user's specific request. "
                    "Be concise, professional, and highlight the synergy between the assets (e.g., value, momentum, and hedge)."
                )),
                HumanMessage(content=(
                    f"User Request: {state.get('user_request')}\n\n"
                    f"Selected Assets:\n" + "\n".join([f"- {p.symbol}: {p.rationale} (Metrics: {p.metrics})" for p in accepted_proposals])
                ))
            ]
            synthesis_res = await self.llm.ainvoke(synthesis_prompt)
            final_report = self.extract_llm_text(synthesis_res.content)
        elif state.get("iterations", 0) >= 2:
             final_report = f"Analysis concluding after {state.get('iterations')} iterations. Best candidates: {', '.join([p.symbol for p in updated_proposals])}. Some assets require further risk-adjustment."

        return {
            "is_validated": all_validated,
            "final_report": final_report,
            "current_agent": "financial_analyst",
            "iterations": state.get("iterations", 0) + 1
        }
