import logging
from typing import Dict, Any
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from app.core.config import settings

logger = logging.getLogger(__name__)

class AlpacaTradeClient:
    """
    Client for dispatching target portfolio weights to Alpaca Paper Trading API.
    """
    def __init__(self):
        self.api_key = getattr(settings, "ALPACA_API_KEY", "")
        self.secret_key = getattr(settings, "ALPACA_SECRET_KEY", "")
        
        # Will fail if keys are empty in a real run, but we catch it gracefully
        if self.api_key and self.secret_key:
            self.client = TradingClient(self.api_key, self.secret_key, paper=True)
        else:
            self.client = None
            logger.warning("Alpaca keys not configured. Paper trading is disabled.")

    async def execute_target_weights(self, target_weights: Dict[str, float]) -> bool:
        """
        Calculates required shares and submits market orders to match target weights.
        Note: True production would calculate current positions vs target. 
        For this prototype pipeline, we demonstrate order dispatch structure.
        """
        if not self.client:
            logger.error("Alpaca client not initialized.")
            return False

        try:
            # 1. Get current account equity
            account = self.client.get_account()
            equity = float(account.equity)
            
            # 2. Issue orders to match target weights
            for symbol, weight in target_weights.items():
                if weight <= 0:
                    continue # Ignore shorting for this prototype
                    
                target_value = equity * weight
                logger.info(f"Targeting ${target_value:.2f} of {symbol}")
                
                # In standard Alpaca, we can use fractional shares via notionals
                market_order_data = MarketOrderRequest(
                    symbol=symbol,
                    notional=target_value,
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.DAY
                )
                
                # Submit Paper Order
                self.client.submit_order(order_data=market_order_data)
                logger.info(f"Successfully dispatched order for {symbol}.")
                
            return True
        except Exception as e:
            logger.error(f"Alpaca execution failed: {e}")
            return False
