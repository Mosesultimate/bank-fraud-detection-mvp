from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import logging
import sys

from app.api.routes import router
from app.database.db import init_db, close_db
from app.services.anomaly_detector import AnomalyDetector
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown events for the FastAPI application
    """
    # Startup
    logger.info("🚀 Starting FraudShield API...")
    
    try:
        # Initialize database
        logger.info("📦 Initializing database...")
        init_db()
        logger.info("✅ Database initialized successfully")
        
        # Load ML model
        logger.info("🤖 Loading fraud detection model...")
        detector = AnomalyDetector.get_instance()
        detector.load_model()  # This will load or initialize the model
        logger.info("✅ Model loaded successfully")
        
    except Exception as e:
        logger.error(f"❌ Startup error: {str(e)}")
        raise
    
    logger.info("✅ FraudShield API started successfully")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down FraudShield API...")
    try:
        close_db()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error(f"❌ Shutdown error: {str(e)}")
    
    logger.info("👋 FraudShield API shut down complete")


app = FastAPI(
    title="FraudShield API",
    description="Bank Transaction Fraud Detection System",
    version="1.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(router)


# Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "details": exc.errors(),
            "path": str(request.url)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later.",
            "path": str(request.url)
        }
    )


@app.get("/")
def home():
    """Root endpoint"""
    return {
        "message": "FraudShield API is live",
        "version": "1.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }
