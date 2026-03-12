from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from app.core.workflow import app_workflow
from app.core.state import AssetProposal
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class AnalysisRequest(BaseModel):
    user_request: str
    
class AnalysisResponse(BaseModel):
    is_validated: bool
    final_report: str | None
    proposals: List[Dict[str, Any]]

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_portfolio(request: AnalysisRequest):
    """
    Trigger the multi-agent analysis workflow.
    """
    initial_state = {
        "user_request": request.user_request,
        "proposals": [],
        "current_agent": "system",
        "is_validated": False,
        "final_report": None
    }
    
    try:
        logger.info(f"Starting analysis workflow for request: {request.user_request}")
        
        # Invoke the LangGraph workflow
        # Note: in a production app, we might want to run this asynchronously 
        # using run_in_executor or similar if it takes a long time,
        # or use LangGraph's async invocation methods.
        final_state = await app_workflow.ainvoke(initial_state)
        
        # Format proposals for JSON response
        formatted_proposals = []
        for prop in final_state.get("proposals", []):
            formatted_proposals.append({
                "symbol": prop.symbol,
                "strategy_type": prop.strategy_type,
                "rationale": prop.rationale,
                "status": prop.status,
                "metrics": prop.metrics,
                "feedback": prop.feedback
            })
            
        return AnalysisResponse(
            is_validated=final_state.get("is_validated", False),
            final_report=final_state.get("final_report"),
            proposals=formatted_proposals
        )
        
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
