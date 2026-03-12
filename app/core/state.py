from typing import List, Dict, Any, Annotated, Optional
import operator
from pydantic import BaseModel, Field

# ---------------------------------------------------------
# Define Models used in State
# ---------------------------------------------------------

class AssetProposal(BaseModel):
    symbol: str
    rationale: str
    strategy_type: str = Field(description="E.g., intrinsic_gap, momentum_factor, macro_hedge")
    metrics: Optional[Dict[str, float]] = None # Populated after backtest
    status: str = Field(default="pending", description="pending, accepted, rejected")
    feedback: Optional[str] = None

# ---------------------------------------------------------
# Define State using TypedDict for LangGraph compatibility
# ---------------------------------------------------------

from typing_extensions import TypedDict

def extend_list(a: List, b: List) -> List:
    return a + b

class PortfolioState(TypedDict):
    """
    Maintains the state of the analysis workflow.
    """
    # The original query/focus from the user
    user_request: str
    
    # List of proposals from specialists, concatenated using `extend_list`
    proposals: Annotated[List[AssetProposal], extend_list]
    
    # Current active sub-task or node the agent is evaluating
    current_agent: str
    
    # Final synthesized report from the Lead Analyst
    final_report: Optional[str]
    
    # Has the portfolio met the gatekeeper's criteria?
    is_validated: bool
