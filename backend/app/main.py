"""
CSV Upload & Auto-Convert Pipeline - Backend API
Main FastAPI application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="CSV Upload API",
    description="Backend API for CSV file upload, validation, and conversion pipeline",
    version="1.0.0"
)

# Configure CORS
allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes will be imported here
# from app.routes import upload


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
