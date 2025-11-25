from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Transaction(Base):
    """Transaction database model"""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False, index=True)
    merchant = Column(String(255), nullable=True)
    category = Column(String(100), nullable=True)
    customer_id = Column(String(100), nullable=True, index=True)
    is_fraud = Column(Boolean, default=False, index=True)
    fraud_score = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    raw_data = Column(Text, nullable=True)  # Store original transaction data as JSON
    
    def __repr__(self):
        return f"<Transaction(id={self.id}, amount={self.amount}, is_fraud={self.is_fraud})>"

