from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, AsyncGenerator
from app.core.workflow import app_workflow
from app.core.state import AssetProposal
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter()

class AnalysisRequest(BaseModel):
    user_request: str
    
class AnalysisResponse(BaseModel):
    is_validated: bool
    final_report: str | None
    proposals: List[Dict[str, Any]]

@router.post("/analyze")
async def analyze_portfolio(request: AnalysisRequest):
    """
    Trigger the multi-agent analysis workflow with real-time streaming events.
    """
    initial_state = {
        "user_request": request.user_request,
        "proposals": [],
        "current_agent": "system",
        "is_validated": False,
        "final_report": None
    }
    
    config = {"configurable": {"thread_id": "default_analysis_thread"}}

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for event in app_workflow.astream_events(initial_state, config, version="v2"):
                kind = event["event"]
                
                # Filter for interesting events to send to the UI
                if kind == "on_chat_model_start":
                    # An agent (model) started thinking
                    yield f"data: {json.dumps({'type': 'agent_start', 'agent': event['name']})}\n\n"
                
                elif kind == "on_tool_start":
                    # A tool (API call) started
                    yield f"data: {json.dumps({'type': 'tool_start', 'tool': event['name'], 'input': event['data'].get('input')})}\n\n"
                
                elif kind == "on_tool_end":
                    # Tool finished
                    yield f"data: {json.dumps({'type': 'tool_end', 'tool': event['name']})}\n\n"
                
                elif kind == "on_chain_end" and event["name"] == "LangGraph":
                    # The final state is available
                    final_state = event["data"].get("output")
                    if final_state:
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
                        
                        yield f"data: {json.dumps({'type': 'final_result', 'is_validated': final_state.get('is_validated', False), 'final_report': final_state.get('final_report'), 'proposals': formatted_proposals})}\n\n"
        
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            yield f"data: {json.dumps({'type': 'error', 'detail': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
