from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import JSONResponse
from typing import List
import pandas as pd
import io
from datetime import datetime

from app.api.schemas import (
    DetectionRequest,
    DetectionResponse,
    TransactionResponse,
    StatsResponse,
    TransactionCreate
)
from app.services.anomaly_detector import AnomalyDetector
from app.services.data_loader import DataLoader
from app.database.db import get_db
from app.database.models import Transaction

router = APIRouter(prefix="/api/v1", tags=["fraud-detection"])

# Dependency to get detector instance
def get_detector():
    """Get anomaly detector instance"""
    return AnomalyDetector.get_instance()


def get_data_loader():
    """Get data loader instance"""
    return DataLoader.get_instance()


@router.post("/upload", response_model=DetectionResponse)
async def upload_transactions(
    file: UploadFile = File(..., description="CSV file with transaction data"),
    detector: AnomalyDetector = Depends(get_detector)
):
    """
    Upload transaction data from CSV file and detect fraud
    """
    try:
        # Validate file type
        if not file.filename or not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV file")
        
        # Read CSV file
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        # Validate required columns
        required_columns = ['amount']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        # Convert to transactions list
        transactions = []
        for _, row in df.iterrows():
            transactions.append(TransactionCreate(
                amount=float(row['amount']),
                merchant=row.get('merchant'),
                category=row.get('category'),
                customer_id=str(row.get('customer_id', ''))
            ))
        
        # Perform fraud detection
        results = detector.detect_batch(transactions)
        
        # Format response
        fraud_count = sum(1 for r in results if r.is_fraud)
        normal_count = len(results) - fraud_count
        
        return DetectionResponse(
            results=results,
            total_transactions=len(results),
            fraud_count=fraud_count,
            normal_count=normal_count
        )
        
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="CSV file is empty")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@router.post("/detect", response_model=DetectionResponse)
async def detect_fraud(
    request: DetectionRequest,
    detector: AnomalyDetector = Depends(get_detector)
):
    """
    Run fraud detection on a list of transactions
    """
    try:
        # Perform fraud detection
        results = detector.detect_batch(request.transactions)
        
        # Calculate statistics
        fraud_count = sum(1 for r in results if r.is_fraud)
        normal_count = len(results) - fraud_count
        
        return DetectionResponse(
            results=results,
            total_transactions=len(results),
            fraud_count=fraud_count,
            normal_count=normal_count
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during detection: {str(e)}")


@router.get("/stats", response_model=StatsResponse)
async def get_statistics(
    db = Depends(get_db)
):
    """
    Get fraud detection statistics
    """
    try:
        # Query database for statistics
        total = db.query(Transaction).count()
        fraud_count = db.query(Transaction).filter(Transaction.is_fraud == True).count()
        normal_count = total - fraud_count
        
        fraud_rate = (fraud_count / total * 100) if total > 0 else 0.0
        
        # Get last transaction timestamp
        last_transaction = db.query(Transaction).order_by(Transaction.timestamp.desc()).first()
        last_updated = last_transaction.timestamp if last_transaction else None
        
        return StatsResponse(
            total_transactions=total,
            fraud_transactions=fraud_count,
            normal_transactions=normal_count,
            fraud_rate=round(fraud_rate, 2),
            last_updated=last_updated
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving statistics: {str(e)}")


@router.get("/health")
async def health_check():
    """
    System health check endpoint
    """
    try:
        # Check database connection
        db_status = "connected"
        try:
            db = next(get_db())
            # Try a simple query
            db.query(Transaction).limit(1).all()
            db.close()
        except Exception:
            db_status = "disconnected"
        
        # Check model status
        detector = AnomalyDetector.get_instance()
        model_loaded = detector.is_model_loaded() if hasattr(detector, 'is_model_loaded') else False
        
        status = "healthy" if db_status == "connected" and model_loaded else "degraded"
        
        return {
            "status": status,
            "version": "1.0",
            "database": db_status,
            "model_loaded": model_loaded,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

