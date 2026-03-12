# Multi-Asset Intelligence Platform

A stateful multi-agent swarm for asset analysis with VectorBT backtesting. This is a Financial Analyst application built with FastAPI, LangGraph, and Google's Gemini models.

## Features

- **Multi-Agent System**: Uses specific agents (Value Analyst, Technical Analyst, Macro & Hedge Fund Analyst, Risk & Compliance Analyst, and Financial Analyst) to synthesize investment proposals.
- **Backtesting Validations**: Leverages VectorBT to backtest the strategies over historical data.
- **FastAPI Backend**: Exposes a REST API (`/api/v1/analyze`) for submitting natural language investment queries.
- **Google Gemini Integration**: Uses `gemini-3.1-pro` model to interpret queries and drive the agent actions.

## Setup

1. Copy `.env.example` to `.env` and fill out your API keys (e.g., Google API Key, Alpha Vantage, Polygon, FRED, News API, and GCP configs).
   ```bash
   cp .env.example .env
   ```

2. **Run Locally (Virtual Environment)**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

3. **Run via Docker**
   ```bash
   docker-compose up --build
   ```

## Usage

Test the API after starting the server:

```bash
python test_api.py
```

Or make a direct `curl` request:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"user_request": "I need a balanced portfolio for the next 2 years"}'
```
