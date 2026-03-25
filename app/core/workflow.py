from langgraph.graph import StateGraph, END
from app.core.state import PortfolioState
import logging

from app.agents.data_engineer import DataEngineerAgent
from app.agents.alpha_generator import AlphaGeneratorAgent
from app.agents.portfolio_optimizer import PortfolioOptimizerAgent
from app.agents.execution_validator import ExecutionValidatorAgent
from app.tools.alpaca_client import AlpacaTradeClient

logger = logging.getLogger(__name__)

# Instantiate standard quantitative agents
data_eng = DataEngineerAgent()
alpha_gen = AlphaGeneratorAgent()
port_opt = PortfolioOptimizerAgent()
exec_val = ExecutionValidatorAgent()

# Node wrappers to adapt class methods for LangGraph
async def data_engineer_node(state: PortfolioState) -> PortfolioState:
    return await data_eng.run(state)

async def alpha_generator_node(state: PortfolioState) -> PortfolioState:
    return await alpha_gen.run(state)

async def portfolio_optimizer_node(state: PortfolioState) -> PortfolioState:
    return await port_opt.run(state)

async def execution_validator_node(state: PortfolioState) -> PortfolioState:
    return await exec_val.run(state)

async def execute_trades_node(state: PortfolioState) -> PortfolioState:
    logger.info("ExecuteTrades: Dispatched to Alpaca API...")
    target_weights = state.get("target_weights", {})
    
    if target_weights:
        alpaca_client = AlpacaTradeClient()
        success = await alpaca_client.execute_target_weights(target_weights)
        if success:
            logger.info("Paper trades dispatched successfully.")
        else:
            logger.error("Paper trade dispatch failed.")
            
    return {"final_weights": target_weights}

def create_workflow(checkpointer=None) -> StateGraph:
    """Builds the multi-agent production execution graph."""
    workflow = StateGraph(PortfolioState)
    
    # 1. Add Nodes
    workflow.add_node("Ingest", data_engineer_node)
    workflow.add_node("Generate_Alpha", alpha_generator_node)
    workflow.add_node("Optimize", portfolio_optimizer_node)
    workflow.add_node("Validate", execution_validator_node)
    workflow.add_node("Execute", execute_trades_node)
    
    # 2. Define Sequential Edges
    workflow.set_entry_point("Ingest")
    workflow.add_edge("Ingest", "Generate_Alpha")
    workflow.add_edge("Generate_Alpha", "Optimize")
    workflow.add_edge("Optimize", "Validate")
    
    # 3. Define Conditional Routing
    def check_validation(state: PortfolioState):
        """
        Routes based on validation metrics.
        Returns to Generate_Alpha if Sharpe < 1.5 or Max DD > 15%.
        """
        if state.get("is_validated", False):
            return "Execute"
        
        if state.get("iterations", 0) >= 3:
            logger.warning("Max iterations reached. Proceeding to execution regardless.")
            return "Execute" 
            
        logger.warning(f"Validation failed (Monte Carlo Prop < 80%). Iterations: {state.get('iterations', 0)}. Looping back to Alpha Generation.")
        return "Generate_Alpha"
        
    workflow.add_conditional_edges(
        "Validate",
        check_validation,
        {
            "Execute": "Execute",
            "Generate_Alpha": "Generate_Alpha"
        }
    )
    
    workflow.add_edge("Execute", END)
    
    return workflow.compile(checkpointer=checkpointer)

app_workflow = create_workflow()
