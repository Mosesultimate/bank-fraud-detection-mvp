from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class TransactionBase(BaseModel):
    """Base transaction schema"""
    amount: float = Field(..., description="Transaction amount", gt=0)
    merchant: Optional[str] = Field(None, description="Merchant name")
    category: Optional[str] = Field(None, description="Transaction category")
    customer_id: Optional[str] = Field(None, description="Customer identifier")


class TransactionCreate(TransactionBase):
    """Schema for creating a transaction"""
    pass


class TransactionResponse(TransactionBase):
    """Schema for transaction response"""
    id: int
    is_fraud: bool = Field(..., description="Fraud detection result")
    fraud_score: float = Field(..., description="Fraud confidence score (0-1)")
    timestamp: datetime
    
    class Config:
        from_attributes = True


class DetectionRequest(BaseModel):
    """Schema for fraud detection request"""
    transactions: List[TransactionCreate] = Field(..., description="List of transactions to analyze")


class DetectionResponse(BaseModel):
    """Schema for fraud detection response"""
    results: List[TransactionResponse] = Field(..., description="Detection results")
    total_transactions: int
    fraud_count: int
    normal_count: int


class StatsResponse(BaseModel):
    """Schema for statistics response"""
    total_transactions: int
    fraud_transactions: int
    normal_transactions: int
    fraud_rate: float
    last_updated: Optional[datetime]


class HealthResponse(BaseModel):
    """Schema for health check response"""
    status: str
    version: str
    database: str
    model_loaded: bool

