from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from api.routes import runs, health
import sys

# Configure structured logging
logger.remove()
logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

app = FastAPI(
    title="Sentinel API",
    description="Backend observability for LangGraph intercept sweeps.",
    version="1.0.0"
)

# Enable CORS for NextJS dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routes
app.include_router(runs.router, prefix="/runs", tags=["Runs"])
app.include_router(health.router, prefix="/health", tags=["Health"])

logger.info("Sentinel API successfully booted and routes mounted.")
