import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.state import PortfolioState
from app.tools.market_data import MarketDataClient
from app.tools.fundamentals import FundamentalsClient
from app.core.config import settings

logger = logging.getLogger(__name__)

# Strict JSON Output Schema
class DataEngineerOutput(BaseModel):
    status: str = Field(description="Status of the ingestion process ('SUCCESS', 'PARTIAL', 'FAILED').")
    imputation_strategy: str = Field(description="Description of how missing data was handled (e.g., 'Forward filled then backward filled').")
    anomalies: List[str] = Field(description="List of detected anomalies (e.g., 'AAPL missing 10 days of data').")
    summary: str = Field(description="A brief summary of the dataset ingested and the features created.")

class DataEngineerAgent:
    """
    Ingests market data and fundamentals, aligns time series, 
    handles imputation, and uses LLM to structure metadata.
    """
    def __init__(self):
        self.market_data = MarketDataClient()
        self.fundamentals = FundamentalsClient()
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-3-flash-preview", 
            temperature=0, 
            api_key=settings.GOOGLE_API_KEY
        )
        
        # Simple CIK mapper for the SEC EDGAR API test
        self.cik_lookup = {
            "AAPL": "0000320193",
            "MSFT": "0000789019",
            "GOOGL": "0001652044",
            "NVDA": "0001045810",
        }
    
    async def run(self, state: PortfolioState) -> PortfolioState:
        universe: List[str] = state.get("universe", ["AAPL", "MSFT", "GOOGL"])
        end_date = state.get("date", datetime.now().strftime("%Y-%m-%d"))
        
        # Calculate start date (e.g., 2 years lookback)
        start_date_obj = datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=365*2)
        start_date = start_date_obj.strftime("%Y-%m-%d")
        
        logger.info(f"Data Engineer initiating for {len(universe)} stocks from {start_date} to {end_date}")
        
        price_dfs = {}
        metadata_ingested = []
        anomalies_detected = []
        
        for symbol in universe:
            # 1. Fetch Market Data
            df = await self.market_data.get_historical_ohlcv(symbol, start_date, end_date)
            if not df.empty:
                price_dfs[symbol] = df['Close']
            else:
                anomalies_detected.append(f"Failed to fetch market data for {symbol}.")
                
            # 2. Fetch Fundamentals & SEC (Testing APIs and Redis caching)
            fmp_metrics = await self.fundamentals.get_key_metrics(symbol)
            if not fmp_metrics:
                anomalies_detected.append(f"Failed FMP metrics for {symbol}.")
                
            cik = self.cik_lookup.get(symbol)
            if cik:
                sec_data = await self.fundamentals.get_sec_filings_metadata(cik)
                metadata_ingested.append(f"{symbol} SEC filings count: {len(sec_data.get('accessionNumber', [])) if sec_data else 0}")
                
        if not price_dfs:
            logger.error("Failed to ingest any price data.")
            return {"raw_data": {"error": "Ingestion Failed"}}
            
        # Align time series (Forward-fill, then backward-fill)
        aligned_close_df = pd.DataFrame(price_dfs)
        nan_count_before = aligned_close_df.isnull().sum().sum()
        
        aligned_close_df.fillna(method='ffill', inplace=True)
        aligned_close_df.fillna(method='bfill', inplace=True) 
        
        # Compute Log returns
        log_returns = np.log(aligned_close_df / aligned_close_df.shift(1))
        log_returns.dropna(inplace=True)
        
        # Use LLM to generate structured summary
        sys_msg = SystemMessage(content=(
            "You are an expert Data Engineer evaluating a quantitative ingestion pipeline. "
            "Based on the provided metadata, output a strict JSON summary of the data quality."
        ))
        
        user_msg = HumanMessage(content=(
            f"Universe: {universe}\n"
            f"Shape: {aligned_close_df.shape}\n"
            f"NaNs before imputation: {nan_count_before}\n"
            f"Anomalies detected by script: {anomalies_detected}\n"
            f"SEC Metadata Sample: {metadata_ingested[:2]}"
        ))
        
        # Bind the Pydantic schema
        structured_llm = self.llm.with_structured_output(DataEngineerOutput)
        
        try:
            llm_result: DataEngineerOutput = await structured_llm.ainvoke([sys_msg, user_msg])
            logger.info(f"Data Engineer Output Status: {llm_result.status}")
        except Exception as e:
            logger.error(f"LLM Structure parsing failed: {e}")
            llm_result = DataEngineerOutput(
                status="PARTIAL", 
                imputation_strategy="Fallback to default", 
                anomalies=[], 
                summary="LLM Summary Failed"
            )
        
        data_payload = {
            "close_prices": aligned_close_df.to_dict(orient="list"),
            "log_returns": log_returns.to_dict(orient="list"),
            "dates": aligned_close_df.index.astype(str).tolist(),
            "metadata": llm_result.dict()
        }
        
        return {"raw_data": data_payload}
