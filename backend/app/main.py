"""
CSV Upload & Auto-Convert Pipeline - Backend API
Main FastAPI application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add converters/src to Python path for CSV converter imports
converters_src = Path(__file__).parent.parent.parent / "converters" / "src"
if str(converters_src) not in sys.path:
    sys.path.insert(0, str(converters_src))

# Load environment variables
load_dotenv()

# Setup logging
from app.upload_logging.config import setup_logging, setup_error_logging
setup_logging()
setup_error_logging()
logger = logging.getLogger(__name__)

# Load configuration
from app.config import Config
Config.ensure_directories()
Config.validate()

# Create FastAPI app
app = FastAPI(
    title="CSV Upload API",
    description="Backend API for CSV file upload, validation, and conversion pipeline",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
allowed_origins = [origin.strip() for origin in Config.CORS_ORIGINS]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routes
from app.routes import upload_router
app.include_router(upload_router)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint to verify server is running"""
    logger.info("Health check called")
    return {
        "status": "ok",
        "service": "CSV Upload API",
        "version": "1.0.0"
    }


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("CSV Upload API starting up...")
    logger.info(f"CORS origins: {allowed_origins}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("CSV Upload API shutting down...")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
