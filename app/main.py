from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os
from app.core.config import settings
from app.api.endpoints import router as api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup - initialize connections here (e.g. BigQuery client)
    print(f"Starting Multi-Asset Intelligence Platform in {settings.ENVIRONMENT} mode")
    yield
    # Cleanup - close connections here
    print("Shutting down")


app = FastAPI(
    title="Multi-Asset Intelligence Platform",
    description="Stateful multi-agent swarm for asset analysis with VectorBT backtesting",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def read_index():
    return FileResponse('app/static/index.html')

@app.get("/health")
async def health_check():
    return {"status": "healthy", "environment": settings.ENVIRONMENT}

