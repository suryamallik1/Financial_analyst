import vectorbt as vbt
import pandas as pd
import numpy as np
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class BacktestEngine:
    """
    Vectorized backtesting engine using VectorBT.
    Refactored to accept target fractional portfolio weights, 
    slippage models, and 0.001% fees.
    """
    
    async def simulate_portfolio(self, close_prices: Dict[str, List[float]], 
                                 target_weights: Dict[str, float], 
                                 fees: float = 0.00001, # 0.001%
                                 slippage: float = 0.0005) -> Dict[str, Any]:
        """
        Runs a vectorized backtest by translating target weights into daily rebalancing orders.
        """
        if not close_prices or not target_weights:
            return {}
            
        prices_df = pd.DataFrame(close_prices)
        if prices_df.empty:
            return {}
            
        # For a true backtest, we need a time series of weights. 
        # In this operational mode, we validate if rebalancing TO these weights TODAY 
        # (and holding) is viable natively, or historically how these signals performed.
        # Since this is a daily pipeline, we simulate the 'last 30 days' performance 
        # assuming these weights were held, to calculate Sharpe/Drawdown constraints.
        
        # Create a weights DataFrame matching the prices index
        weights_df = pd.DataFrame(index=prices_df.index, columns=prices_df.columns)
        for symbol, weight in target_weights.items():
            if symbol in weights_df.columns:
                weights_df[symbol] = weight
        weights_df.fillna(0.0, inplace=True)
        
        try:
            # VectorBT standard portfolio from orders 
            # size_type=2 means 'targetpercent'
            portfolio = vbt.Portfolio.from_orders(
                prices_df,
                size=weights_df,
                size_type='targetpercent',
                freq='1d',
                init_cash=100000.0,
                fees=fees,
                slippage=slippage
            )
            
            return self._calculate_metrics(portfolio)
        except Exception as e:
            logger.error(f"VectorBT simulation failed: {e}")
            return {}

    def _calculate_metrics(self, portfolio: vbt.Portfolio) -> Dict[str, Any]:
        """Extracts and formats key metrics for the LangGraph state."""
        try:
            sharpe = portfolio.sharpe_ratio()
            # VectorBT returns Sharpe as array if multiple columns, but we supplied exact matrix
            if isinstance(sharpe, pd.Series):
                sharpe = sharpe.mean() # Aggregate
                
            max_dd = portfolio.max_drawdown()
            if isinstance(max_dd, pd.Series):
                max_dd = max_dd.min() # Max drawdown is usually a negative number
                
            # Convert to absolute percentage for max_dd
            max_dd_perc = abs(float(max_dd)) * 100 if not pd.isna(max_dd) else 0.0
            
            metrics = {
                "total_return": float(portfolio.total_return().mean() if isinstance(portfolio.total_return(), pd.Series) else portfolio.total_return()),
                "sharpe_ratio": float(sharpe) if not pd.isna(sharpe) else 0.0,
                "max_drawdown": max_dd_perc
            }
            return metrics
        except Exception as e:
            logger.error(f"Metric calculation error: {e}")
            return {"sharpe_ratio": 0.0, "max_drawdown": 100.0}
