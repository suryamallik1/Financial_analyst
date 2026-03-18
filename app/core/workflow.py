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
    
    # 1. Add nodes
    workflow.add_node("Lead_Planner", fin_analyst.plan)
    workflow.add_node("Value_Analyst", value_agent.run)
    workflow.add_node("Technical_Analyst", tech_agent.run)
    workflow.add_node("Risk_Compliance", risk_agent.run)
    workflow.add_node("Lead_Validator", fin_analyst.run)
    
    # 2. Define edges
    workflow.set_entry_point("Lead_Planner")
    
    workflow.add_edge("Lead_Planner", "Value_Analyst")
    workflow.add_edge("Value_Analyst", "Technical_Analyst")
    workflow.add_edge("Technical_Analyst", "Risk_Compliance")
    workflow.add_edge("Risk_Compliance", "Lead_Validator")
    
    # 3. Refinement Logic
    def should_continue(state: PortfolioState):
        if state.get("final_report") is not None or state.get("iterations", 0) >= 3:
            return "end"
        return "refine"
            
    workflow.add_conditional_edges(
        "Lead_Validator",
        should_continue,
        {
            "end": END,
            "refine": "Value_Analyst"
        }
    )
    
    memory = MemorySaver()
    
    return workflow.compile(checkpointer=memory)
    
# Export the compiled runner
app_workflow = create_workflow()
