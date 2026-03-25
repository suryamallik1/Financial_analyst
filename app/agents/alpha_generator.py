import pandas as pd
import numpy as np
import logging
import itertools
from typing import Dict, Any, List
from statsmodels.tsa.stattools import coint
from app.core.state import PortfolioState
from app.tools.macro_data import MacroDataClient

logger = logging.getLogger(__name__)

class AlphaGeneratorAgent:
    """
    Computes Pro-Level mathematical signals:
    - Blended Momentum (Cross-Sectional Rank + Time-Series Trend)
    - Statistical Arbitrage (Cointegration Spreads across Correlated Pairs)
    - Volatility Scaling (GDELT NLP proxy)
    """
    def __init__(self):
        self.macro_data = MacroDataClient()
        
    async def run(self, state: PortfolioState) -> PortfolioState:
        logger.info("AlphaGenerator (Pro-Level): Starting signal generation...")
        
        raw_data = state.get("raw_data", {})
        if "error" in raw_data or not raw_data:
            logger.error("No raw data available for Alpha Generation.")
            return {"alpha_signals": {}}
            
        universe = state.get("universe", [])
        
        # Reconstruct DataFrame from dictionary payload
        close_dict = raw_data.get("close_prices", {})
        prices_df = pd.DataFrame(close_dict)
        
        signals = {symbol: 0.0 for symbol in universe}
        
        if prices_df.empty or len(prices_df) < 50:
            logger.warning("Insufficient length for robust modeling. Returning neutral signals.")
            return {"alpha_signals": signals}
            
        # 1. Pro-Level Momentum (Time-Series + Cross-Sectional)
        # Calculate 20-day returns for Cross-Sectional rank
        returns_20d = prices_df.pct_change(20).iloc[-1]
        z_scores = (returns_20d - returns_20d.mean()) / returns_20d.std()
        
        # Calculate Time-Series Trend (e.g., Price vs 50-day SMA ratio)
        sma_50 = prices_df.rolling(window=50).mean().iloc[-1]
        trend_ratio = (prices_df.iloc[-1] / sma_50) - 1.0
        
        for symbol in universe:
            if symbol in z_scores and symbol in trend_ratio:
                # Blend the cross-sectional momentum rank with the absolute time-series trend
                # A stock is extremely strong if it beats its peers AND its own historical long-term average
                blended_mom = (z_scores[symbol] * 0.5) + (trend_ratio[symbol] * 10 * 0.5)
                signals[symbol] += blended_mom

        # 2. Pro-Level Mean Reversion (Cointegration Pairs instead of raw ADF)
        # Find highly cointegrated pairs. If they diverge, trade the convergence.
        logger.info("Calculating Cointegration Spreads...")
        for pair in itertools.combinations(universe, 2):
            sym1, sym2 = pair
            if sym1 in prices_df and sym2 in prices_df:
                try:
                    s1 = prices_df[sym1].dropna()
                    s2 = prices_df[sym2].dropna()
                    
                    # Ensure series length matches
                    common_index = s1.index.intersection(s2.index)
                    if len(common_index) > 50:
                        s1 = s1.loc[common_index]
                        s2 = s2.loc[common_index]
                        
                        score, pvalue, _ = coint(s1, s2)
                        if pvalue < 0.05:
                            # The pair is cointegrated. Check current spread vs historical mean
                            ratio = s1 / s2
                            z_spread = (ratio.iloc[-1] - ratio.mean()) / ratio.std()
                            
                            # If z_spread > 1.5, sym1 is historically overpriced relative to sym2
                            # Short sym1, Long sym2
                            if z_spread > 1.5:
                                signals[sym1] -= reversed_scale_factor(z_spread)
                                signals[sym2] += reversed_scale_factor(z_spread)
                            elif z_spread < -1.5:
                                signals[sym1] += reversed_scale_factor(abs(z_spread))
                                signals[sym2] -= reversed_scale_factor(abs(z_spread))
                except Exception as e:
                    pass
        
        # 3. GDELT NLP (Volatility Scaling)
        # Instead of a strict penalty, scale down signals proportionally if global volatility jumps
        logger.info("Fetching GDELT macro sentiment for volatility scaling...")
        gdelt_data = await self.macro_data.get_gdelt_sentiment("global markets")
        
        # Scale range: 1.0 (calm) to 0.5 (high volatility cutting confidence in half)
        # Assuming gdelt_data presence = minor volatility proxy for this prototype test
        volatility_scalar = 0.7 if gdelt_data else 1.0 
        
        for symbol in signals:
            signals[symbol] = round(signals[symbol] * volatility_scalar, 4)
            
        logger.info(f"Pro-Level Alpha signals generated for {len(signals)} assets.")
        return {"alpha_signals": signals}

def reversed_scale_factor(z: float) -> float:
    """Helper to convert a Z-score divergence into an alpha signal injection."""
    return min(z * 0.1, 0.5) # Cap the injection at 0.5 signal impact
