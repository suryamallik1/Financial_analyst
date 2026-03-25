from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
from app.core.tasks import run_daily_pipeline
from app.core.config import settings
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
import psycopg

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/state")
async def get_latest_state() -> Dict[str, Any]:
    """
    Reads the latest finalized daily pipeline state from PostgreSQL.
    """
    try:
        async with await psycopg.AsyncConnection.connect(settings.POSTGRES_URL, autocommit=True) as conn:
            checkpointer = AsyncPostgresSaver(conn)
            await checkpointer.setup()
            
            # Retrieve the most recent state using the daily thread prefix
            # In a full production UI, we'd list threads or fetch by exact date.
            # Here we grab the default daily thread structure we set in tasks.py
            from datetime import datetime
            today = datetime.now().strftime("%Y-%m-%d")
            thread_id = f"daily_run_{today}"
            config = {"configurable": {"thread_id": thread_id}}
            
            saved_state = await checkpointer.aget(config)
            
            if saved_state and "channel_values" in saved_state:
                return saved_state["channel_values"]
                
            # MOCK FOR Proactive UI TESTING (since Celery API keys are missing)
            return {
                "final_weights": {
                    "AAPL": 0.35,
                    "NVDA": 0.28,
                    "MSFT": 0.22,
                    "TSLA": 0.10,
                    "BTC": 0.05
                },
                "backtest_metrics": {"Sharpe_Ratio": 2.1, "Max_Drawdown": -0.12},
                "is_validated": True,
                "status": "Mocked overnight state."
            }
            
    except Exception as e:
        logger.error(f"Failed to read state from DB: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed.")

@router.post("/trigger")
async def trigger_pipeline():
    """
    Manually triggers the daily quantitative pipeline via Celery worker.
    """
    try:
        task = run_daily_pipeline.delay()
        return {"status": "Pipeline triggered successfully.", "task_id": task.id}
    except Exception as e:
        logger.error(f"Failed to trigger Celery task: {e}")
        raise HTTPException(status_code=500, detail="Failed to communicate with Celery broker.")
