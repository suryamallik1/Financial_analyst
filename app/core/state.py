from typing import TypedDict, List, Dict, Any, Annotated

def merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Custom reducer to merge dictionaries (e.g., signals, raw data)."""
    res = a.copy()
    res.update(b)
    return res

class PortfolioState(TypedDict):
    """
    State definition for the Production Quantitative Map-Reduce Pipeline.
    """
    # Metadata
    date: str
    universe: List[str]
    iterations: int
    
    # Pipeline Data
    raw_data: Annotated[Dict[str, Any], merge_dicts]
    alpha_signals: Annotated[Dict[str, float], merge_dicts]
    target_weights: Dict[str, float]
    
    # Validation & Output
    backtest_metrics: Dict[str, Any]
    is_validated: bool
    final_weights: Dict[str, float]
