import pandas as pd
import logging
from typing import Dict, Any
from pypfopt import HRPOpt
from app.core.state import PortfolioState

logger = logging.getLogger(__name__)

class PortfolioOptimizerAgent:
    """
    Transforms returns into noise-resistant allocations using
    Hierarchical Risk Parity (HRP), and tilts those risk-clustered
    weights based on the Alpha signals computed by the Generator.
    """
    def __init__(self):
        pass
        
    async def run(self, state: PortfolioState) -> PortfolioState:
        logger.info("PortfolioOptimizer (Pro-Level): Computing HRP allocations...")
        
        raw_data = state.get("raw_data", {})
        signals = state.get("alpha_signals", {})
        
        if not raw_data or "error" in raw_data or not signals:
            logger.error("Missing data or signals for Optimization.")
            return {"target_weights": {}}
            
        close_dict = raw_data.get("close_prices", {})
        prices_df = pd.DataFrame(close_dict)
        
        if prices_df.empty or len(prices_df) < 30:
            return {"target_weights": {}}
            
        target_weights = {}
        try:
            # 1. Hierarchical Risk Parity (HRP)
            # HRP requires historical returns, not just a covariance matrix.
            returns_df = prices_df.pct_change().dropna()
            
            # Run the agglomerative clustering algorithm
            hrp = HRPOpt(returns=returns_df)
            hrp_weights = hrp.optimize()
            
            # Clean tiny numeric fragments
            hrp_weights = hrp.clean_weights()
            
            # 2. Alpha Signal Tilt Overlay
            # HRP ignores returns entirely and focuses purely on risk clustering.
            # To actually generate Alpha, we tilt the defensive HRP weights using our Z-scores.
            
            max_signal = max([abs(v) for v in signals.values()]) if signals else 1.0
            max_signal = max_signal if max_signal > 0 else 1.0
            
            tilted_weights = {}
            total_tilt = 0.0
            
            for symbol, base_weight in hrp_weights.items():
                if symbol in signals:
                    # Normalize signal to a -1 to +1 scalar
                    signal_strength = signals[symbol] / max_signal
                    
                    # If signal is negative, we drop weight to 0 for a long-only portfolio
                    if signal_strength <= 0:
                        tilted_weights[symbol] = 0.0
                    else:
                        # Tilt the HRP risk weight UP based on signal conviction
                        # A strength of 1.0 doubles the HRP weight
                        tilted_weights[symbol] = base_weight * (1.0 + signal_strength)
                        total_tilt += tilted_weights[symbol]
                else:
                    tilted_weights[symbol] = base_weight
                    total_tilt += base_weight
            
            # 3. Re-Normalize Weights to sum to 1.0 (100% capital deployment)
            if total_tilt > 0:
                target_weights = {k: round(v / total_tilt, 4) for k, v in tilted_weights.items()}
            else:
                target_weights = hrp_weights
            
            logger.info("HRP Optimization and Alpha Overlay successful.")
            
        except Exception as e:
            logger.error(f"PyPortfolioOpt HRP failed: {e}")
            target_weights = {}

        return {"target_weights": dict(target_weights)}
