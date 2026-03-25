# Multi-Asset Intelligence Platform

A production-grade, stateful multi-agent swarm for institutional-style asset analysis, leveraging **LangGraph** for orchestration, **VectorBT** for backtesting, and **Celery** for asynchronous task execution.

## 🧠 Multi-Agent Architecture

The platform follows an **Orchestrator-Centric** model where specific agents handle distinct layers of the quantitative pipeline:

### 1. Data Engineer Agent
*   **Function**: Ingests and cleans multi-source financial data.
*   **Workflow**: 
    - Fetches historical OHLCV from **yfinance** and key metrics from **Financial Modeling Prep (FMP)**.
    - Retrieves SEC filing metadata via **EDGAR API**.
    - Performs time-series alignment and handles missing data using forward/backward imputation.
    - Uses **Gemini 3.5 Flash** to analyze data quality and generate structured metadata summaries.

### 2. Alpha Generator Agent
*   **Function**: Computes "Pro-Level" mathematical signals to identify market opportunities.
*   **Workflow**:
    - **Blended Momentum**: Combines Cross-Sectional Z-scores (relative strength) with Time-Series Trend (price vs 50-day SMA).
    - **Statistical Arbitrage**: Scans the universe for cointegrated pairs (P-value < 0.05) and generates mean-reversion signals based on spread divergence.
    - **Volatility Scaling**: Integrates **GDELT NLP** sentiment to scale down signals if global market volatility risks increase.

### 3. Portfolio Optimizer Agent
*   **Function**: Transforms alpha signals into noise-resistant capital allocations.
*   **Workflow**:
    - Uses **Hierarchical Risk Parity (HRP)** to cluster assets by risk profile, ensuring a defensive base allocation.
    - Overlays an **Alpha Signal Tilt** that increases weights for high-conviction signals while maintaining a long-only constraint.

### 4. Execution Validator Agent
*   **Function**: Acts as a quantitative gatekeeper using statistical significance testing.
*   **Workflow**:
    - Runs a base chronological backtest with realistic fees (0.1%) and slippage.
    - **Monte Carlo Bootstrap**: Performs **1,000 randomized simulations** of the strategy returns to distinguish "Skill" from "Luck."
    - **Confidence Gating**: Only validates the strategy if it achieves a target Sharpe ratio in **>80%** of simulated market conditions.

---

## ⚙️ Backend & Infrastructure

### Services
- **FastAPI**: Provides a RESTful interface for triggering pipelines (`/api/v1/trigger`) and polling state (`/api/v1/state`).
- **Celery**: Orchestrates background tasks, allowing for long-running quantitative simulations without blocking the API.
- **Redis**: Functions as the Celery message broker and a high-performance cache for API data.
- **PostgreSQL**: Serves as the **LangGraph Checkpointer**. It persists the internal state of every agent run, allowing for thread-based resuming and historical state audits.

### Core Tools
- **MarketDataClient**: Unified wrapper for yfinance and FMP.
- **AlpacaTradeClient**: Handles paper trading execution via the Alpaca Markets API.
- **BacktestEngine**: Specialized engine for simulating portfolio performance metrics.
- **MacroDataClient**: Fetches GDELT sentiment and economic indicators.

---

## 🧪 Testing & Validation

The application includes a robust testing suite to ensure pipeline integrity:

### Automated Tests
- **Pytest Suite**: Located in `/tests/`, focusing on unit logic like time-series alignment, imputation accuracy, and mathematical signal correctness.
- **Integration Tests**: `test_pipeline.py` and `test_full_swarm.py` verify the end-to-end flow from data ingestion to final weight generation.

### Verified Scenarios
- ✅ **Data Alignment**: Ensuring multiple tickers with different holiday schedules align into a singular contiguous dataframe.
- ✅ **State Persistence**: Verifying that PostgreSQL correctly captures agent transitions in the LangGraph workflow.
- ✅ **Monte Carlo Logic**: Validating that the statistical gatekeeper correctly rejects low-confidence/overfitted strategies.

---

## 🚀 Setup & Deployment

1.  **Environment Setup**:
    Copy `.env.example` to `.env` and provide your API keys for Gemini, FMP, and Alpaca.
2.  **Docker Run (Recommended)**:
    ```bash
    docker-compose up --build
    ```
    This launches the API, Worker, Beat, Postgres, and Redis services in sync.
3.  **Local Development**:
    ```bash
    pip install -r requirements.txt
    uvicorn app.main:app --reload
    ```
