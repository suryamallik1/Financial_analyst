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

def merge_proposals(existing: List[AssetProposal], new: List[AssetProposal]) -> List[AssetProposal]:
    """
    Merging strategy that updates existing proposals if the symbol matches,
    otherwise appends the new proposal.
    """
    merged = {p.symbol: p for p in existing}
    for p in new:
        if p.symbol in merged:
            # Update existing proposal fields while keeping persistent ones if needed
            merged[p.symbol].rationale = p.rationale
            merged[p.symbol].strategy_type = p.strategy_type
            if p.metrics:
                merged[p.symbol].metrics = p.metrics
            if p.status != "pending":
                merged[p.symbol].status = p.status
            if p.feedback:
                merged[p.symbol].feedback = p.feedback
        else:
            merged[p.symbol] = p
    return list(merged.values())

class PortfolioState(TypedDict):
    """
    Maintains the state of the analysis workflow.
    """
    # The original query/focus from the user
    user_request: str
    
    # List of proposals from specialists, concatenated using `merge_proposals`
    proposals: Annotated[List[AssetProposal], merge_proposals]
    
    # Current active sub-task or node the agent is evaluating
    current_agent: str
    
    # Final synthesized report from the Lead Analyst
    final_report: Optional[str]
    
    # Instructions from the Lead Analyst to the specialists
    analysis_plan: Optional[str]
    
    # Has the portfolio met the gatekeeper's criteria?
    is_validated: bool
    # Number of refinement iterations
    iterations: int
