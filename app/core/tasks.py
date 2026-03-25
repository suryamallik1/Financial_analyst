import asyncio
import logging
from app.core.celery_app import celery_app
from app.core.workflow import app_workflow
from app.core.config import settings
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from datetime import datetime
import psycopg

logger = logging.getLogger(__name__)

async def _run_pipeline_async():
    """
    Asynchronous executor for the LangGraph quantitative pipeline.
    Uses AsyncPostgresSaver for state persistence.
    """
    logger.info("Starting Daily Quantitative Pipeline execution...")
    
    # Connect to PostgreSQL for Checkpointing
    async with await psycopg.AsyncConnection.connect(settings.POSTGRES_URL, autocommit=True) as conn:
        checkpointer = AsyncPostgresSaver(conn)
        # Ensure the schema exists
        await checkpointer.setup()
        
        # Compile workflow with the checkpointer
        # Note: app_workflow is already compiled in workflow.py, but we can recompile or 
        # structure it to accept the checkpointer here.
        from app.core.workflow import create_workflow
        workflow_with_memory = create_workflow(checkpointer=checkpointer)
        
        # Initial State
        today = datetime.now().strftime("%Y-%m-%d")
        initial_state = {
            "date": today,
            "universe": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"], # Placeholder for 100-stock universe
            "iterations": 0,
            "raw_data": {},
            "alpha_signals": {},
            "target_weights": {},
            "backtest_metrics": {},
            "is_validated": False,
            "final_weights": {}
        }
        
        # Thread configuration for LangGraph checkpointing
        config = {"configurable": {"thread_id": f"daily_run_{today}"}}
        
        try:
            # Execute the graph
            final_state = await workflow_with_memory.ainvoke(initial_state, config=config)
            logger.info("Daily Pipeline completed successfully.")
            return final_state
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            raise

@celery_app.task(name="app.core.tasks.run_daily_pipeline")
def run_daily_pipeline():
    """
    Celery task entry point. Wraps the async execution in a sync function.
    """
    return asyncio.run(_run_pipeline_async())
