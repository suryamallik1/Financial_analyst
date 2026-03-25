import asyncio
import logging
from app.core.workflow import app_workflow
from app.core.state import PortfolioState
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_full_swarm():
    logger.info("Initializing Full Quantitative Swarm Test...")
    
    # 1. Setup Initial State
    initial_state: PortfolioState = {
        "date": "2026-03-18",
        "universe": ["AAPL", "MSFT", "GOOGL"], # Small subset for speed
        "iterations": 0,
        "raw_data": {},
        "alpha_signals": {},
        "target_weights": {},
        "backtest_metrics": {},
        "is_validated": False,
        "final_weights": {}
    }
    
    # 2. Run Graph
    logger.info("Executing Map-Reduce Pipeline...")
    try:
        final_state = await app_workflow.ainvoke(initial_state)
        
        # 3. Print Results
        logger.info("\n=== FULL SWARM PIPELINE RESULTS ===")
        
        data = final_state.get("raw_data", {})
        if "metadata" in data:
            logger.info(f"[Data Engineer] Status: {data['metadata'].get('status')}")
            
        signals = final_state.get("alpha_signals", {})
        logger.info(f"[Alpha Generator] Computed Signals: {signals}")
        
        weights = final_state.get("target_weights", {})
        logger.info(f"[Portfolio Optimizer] Extracted Weights: {weights}")
        
        metrics = final_state.get("backtest_metrics", {})
        logger.info(f"[Execution Validator] Validated Metrics: {metrics}")
        
        is_val = final_state.get("is_validated")
        logger.info(f"[Gatekeeper] Passed Thresholds? {is_val}")
        
        logger.info(f"[Alpaca Node] Final Logged Weights: {final_state.get('final_weights')}")
        
    except Exception as e:
        logger.error(f"Swarm encountered a critical failure: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_full_swarm())
