import logging
import numpy as np
import pandas as pd
from typing import Dict, Any
from app.core.state import PortfolioState
from app.tools.backtest import BacktestEngine

logger = logging.getLogger(__name__)

class ExecutionValidatorAgent:
    """
    Pro-Level Quantitative gatekeeper:
    Uses Monte Carlo resampling on the target portfolio returns to 
    ensure the strategy's Sharpe ratio is statistically robust (Skill),
    rather than a single lucky chronological path (Luck).
    """
    def __init__(self):
        self.backtest_engine = BacktestEngine()
        self.monte_carlo_simulations = 1000
        
    async def run(self, state: PortfolioState) -> PortfolioState:
        logger.info("ExecutionValidator (Pro-Level): Simulating Target Weights...")
        
        target_weights = state.get("target_weights", {})
        raw_data = state.get("raw_data", {})
        iterations = state.get("iterations", 0)
        
        if not target_weights or not raw_data:
            logger.error("Missing weights or data for validation.")
            return {"is_validated": False}
            
        close_prices = raw_data.get("close_prices", {})
        
        # 1. Base Chronological Simulation
        # Simulate passing the target weights into a VectorBT environment 
        # handling 0.001% fees and basic slippage.
        metrics = await self.backtest_engine.simulate_portfolio(close_prices, target_weights)
        
        # In a real setup, backtest_engine would return the daily portfolio returns array.
        # Since we're demonstrating the Pro-Level Monte Carlo logic on top of the workflow,
        # we will extract the chronological log returns from state to simulate portfolio returns.
        
        log_returns = raw_data.get("log_returns", {})
        returns_df = pd.DataFrame(log_returns)
        
        # Calculate chronological portfolio returns
        weights_array = np.array([target_weights.get(col, 0.0) for col in returns_df.columns])
        portfolio_returns = returns_df.dot(weights_array)
        
        # 2. Monte Carlo Permutation (Testing "Luck vs Skill")
        # We bootstrap sample the daily portfolio returns to generate entirely new market paths.
        logger.info(f"Running {self.monte_carlo_simulations} Monte Carlo Paths...")
        
        passed_simulations = 0
        target_sharpe_threshold = 1.0 # The Sharpe ratio we want the portfolio to consistently beat
        
        try:
            # Vectorized Monte Carlo Bootstrap
            # Shape: (number of daily returns, number of simulations)
            randomized_paths = np.random.choice(
                portfolio_returns.dropna().values, 
                size=(len(portfolio_returns), self.monte_carlo_simulations), 
                replace=True
            )
            
            # Calculate annualized Sharpe for every randomized path
            # Assuming 252 trading days for annualization factor
            simulated_means = randomized_paths.mean(axis=0) * 252
            simulated_stds = randomized_paths.std(axis=0) * np.sqrt(252)
            
            # Avoid divide-by-zero
            simulated_stds[simulated_stds == 0] = 1e-6
            
            simulated_sharpes = simulated_means / simulated_stds
            
            # How many randomized paths achieved a Sharpe > our threshold?
            passed_simulations = np.sum(simulated_sharpes > target_sharpe_threshold)
            
        except Exception as e:
            logger.error(f"Monte Carlo Bootstrap failed: {e}")
            
        # 3. Probability Gating
        probability_of_success = passed_simulations / self.monte_carlo_simulations
        logger.info(f"Monte Carlo Probability of Success (Sharpe > {target_sharpe_threshold}): {probability_of_success:.2%}")
        
        metrics["monte_carlo_probability"] = probability_of_success
        
        # Pro-Level Gate: Strategy must succeed in >80% of randomized market conditions to prove 'Skill'
        if probability_of_success > 0.80:
            logger.info("Portfolio PASSED Pro-Level Monte Carlo validation (Statistically Significant Skill).")
            is_valid = True
        else:
            logger.warning(f"Portfolio FAILED validation. Probability {probability_of_success:.2%} is below the 80% confidence threshold (Likely Luck-driven).")
            is_valid = False
            
        return {
            "is_validated": is_valid,
            "backtest_metrics": metrics,
            "iterations": iterations + 1
        }
