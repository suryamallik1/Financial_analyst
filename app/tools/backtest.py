import vectorbt as vbt
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple

class BacktestEngine:
    """
    Vectorized backtesting engine wrapper using VectorBT.
    """
    
    @staticmethod
    def run_backtest(
        price_data: pd.DataFrame, 
        entries: pd.Series, 
        exits: pd.Series,
        freq: str = '1d',
        fees: float = 0.001
    ) -> Dict[str, Any]:
        """
        Runs a vectorized backtest on the given price data and signals.
        
        Args:
            price_data: DataFrame with at least a 'Close' column indexed by Datetime.
            entries: Boolean Series indicating entry signals.
            exits: Boolean Series indicating exit signals.
            freq: Data frequency ('1d', '1h', etc.).
            fees: Trading fee percentage (0.001 = 0.1%).
            
        Returns:
            Dictionary containing key performance metrics.
        """
        if 'Close' not in price_data.columns:
            raise ValueError("Price data must contain a 'Close' column")

        # Create portfolio from signals
        portfolio = vbt.Portfolio.from_signals(
            price_data['Close'],
            entries,
            exits,
            freq=freq,
            fees=fees,
            init_cash=100000.0,
            short_cash=None # Long only for now
        )

        return BacktestEngine._calculate_metrics(portfolio)
        
    @staticmethod
    def run_buy_and_hold(price_data: pd.DataFrame, freq: str = '1d') -> Dict[str, Any]:
        """
        Runs a benchmark buy and hold strategy.
        """
        if 'Close' not in price_data.columns:
             raise ValueError("Price data must contain a 'Close' column")
             
        # Create a single entry at the beginning, no exits
        entries = pd.Series(False, index=price_data.index)
        entries.iloc[0] = True
        
        exits = pd.Series(False, index=price_data.index)
        
        portfolio = vbt.Portfolio.from_signals(
            price_data['Close'],
            entries,
            exits,
            freq=freq,
            init_cash=100000.0
        )
        
        return BacktestEngine._calculate_metrics(portfolio)

    @staticmethod
    def _calculate_metrics(portfolio: vbt.Portfolio) -> Dict[str, Any]:
        """
        Extracts and formats key performance metrics from a VectorBT Portfolio.
        """
        
        # Calculate Win Rate explicitly using trades
        trades = portfolio.trades
        win_rate = trades.win_rate() if len(trades) > 0 else 0.0

        metrics = {
            "Total_Return": portfolio.total_return(),
            "Annualized_Return": portfolio.annualized_return(),
            "Sharpe_Ratio": portfolio.sharpe_ratio(),
            "Sortino_Ratio": portfolio.sortino_ratio(),
            "Max_Drawdown": portfolio.max_drawdown(),
            "Win_Rate": win_rate,
            "Total_Trades": len(trades)
        }
        
        # Convert NumPy floats to standard Python floats for JSON serialization later
        return {k: float(v) if not pd.isna(v) else 0.0 for k, v in metrics.items()}
