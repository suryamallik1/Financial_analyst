from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.core.state import PortfolioState
from app.agents.value_analyst import ValueAnalystAgent
from app.agents.technical_analyst import TechnicalAnalystAgent
from app.agents.risk_compliance import RiskComplianceAgent
from app.agents.financial_analyst import FinancialAnalystAgent
import logging

logger = logging.getLogger(__name__)

# Initialize agents
value_agent = ValueAnalystAgent()
tech_agent = TechnicalAnalystAgent()
risk_agent = RiskComplianceAgent()
fin_analyst = FinancialAnalystAgent()

def create_workflow() -> StateGraph:
    """Builds the multi-agent execution graph."""
    
    workflow = StateGraph(PortfolioState)
    
    # 1. Add nodes for each specialist
    workflow.add_node("Value_Analyst", value_agent.run)
    workflow.add_node("Technical_Analyst", tech_agent.run)
    workflow.add_node("Risk_Compliance", risk_agent.run)
    workflow.add_node("Financial_Analyst", fin_analyst.run)
    
    # 2. Define routing logic
    # Start -> Specialists (Parallel execution via conditional edge logic in a real app,
    # or sequential. For simplicity here, we'll run them sequentially then fan-in)
    
    # Let's orchestrate: Orchestrator kicks off specialists
    def create_initial_state(user_request: str) -> dict:
         return {
             "user_request": user_request,
             "proposals": [],
             "current_agent": "system",
             "is_validated": False,
             "final_report": None
         }
         
    workflow.set_entry_point("Value_Analyst")
    workflow.add_edge("Value_Analyst", "Technical_Analyst")
    workflow.add_edge("Technical_Analyst", "Risk_Compliance")
    workflow.add_edge("Risk_Compliance", "Financial_Analyst")
    
    # 3. The Refinement Loop / Gatekeeper logic
    def should_continue(state: PortfolioState) -> str:
        """
        Determines if the portfolio is validated or needs refinement.
        """
        if state.get("is_validated", False):
            logger.info("Portfolio validated by Financial Analyst. Proceeding to END.")
            return "end"
        else:
            logger.info("Portfolio NOT validated. Loop back for refinement (Technical Analyst in this example).")
            # In a real app we'd target the specific specialist that failed.
            # Here, we send back to tech analyst to regenerate momentum signal
            return "refine"
            
    workflow.add_conditional_edges(
        "Financial_Analyst",
        should_continue,
        {
            "end": END,
            "refine": "Technical_Analyst" # Loop back
        }
    )
    
    memory = MemorySaver()
    
    return workflow.compile(checkpointer=memory)
    
# Export the compiled runner
app_workflow = create_workflow()
