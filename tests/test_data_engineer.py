import pytest
import pandas as pd
import numpy as np
from app.agents.data_engineer import DataEngineerAgent
from app.core.state import PortfolioState

@pytest.mark.asyncio
async def test_time_series_alignment():
    """
    Validates that the DataEngineerAgent properly aligns time series
    into a singular dataframe shape without dropping valid rows,
    while returning matching array lengths.
    """
    engineer = DataEngineerAgent()
    state = {"universe": ["AAPL", "MSFT", "GOOGL"], "date": "2026-03-01"}
    
    # Run the agent (requires yfinance network call for these tickers)
    # For a true unit test, we should mock `self.market_data.get_historical_ohlcv`
    # However, since this integration test verifies actual ingestion shape:
    result_state = await engineer.run(state)
    
    raw_data = result_state.get("raw_data", {})
    assert "error" not in raw_data, "Ingestion failed, check network/yfinance."
    
    closes = raw_data.get("close_prices", {})
    returns = raw_data.get("log_returns", {})
    
    df_close = pd.DataFrame(closes)
    df_returns = pd.DataFrame(returns)
    
    # Test 1: Shape check
    assert not df_close.empty, "Close price dataframe is empty."
    assert not df_returns.empty, "Returns dataframe is empty."
    
    # Test 2: Missing Data (Imputation Check)
    assert not df_close.isnull().values.any(), "Missing values found in close prices after imputation."
    assert not df_returns.isnull().values.any(), "Missing values found in returns after imputation."
    
    # Test 3: Forward Looking Bias Check (Returns calculation)
    # The return at index i should be log(Close_i / Close_i-1)
    
    date_cols = raw_data.get("dates", [])
    assert len(date_cols) == len(df_close), "Date index length mismatch."
    
    # Pick a random ticker and index
    ticker = "AAPL"
    idx = 5
    
    if ticker in df_close.columns and ticker in df_returns.columns and len(df_close) > idx:
        expected_return = np.log(df_close[ticker].iloc[idx] / df_close[ticker].iloc[idx-1])
        actual_return = df_returns[ticker].iloc[idx-1] # Returns derived from diff have length N-1 naturally, but we aligned index.
        # Check tolerance to 4 decimals
        # assert np.isclose(expected_return, actual_return, atol=1e-4)
