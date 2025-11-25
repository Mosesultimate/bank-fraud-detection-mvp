import numpy as np
import pandas as pd
from typing import List, Optional
from datetime import datetime
import logging
import os
from pathlib import Path
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib

from app.api.schemas import TransactionCreate, TransactionResponse
from app.core.config import settings

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """
    Anomaly detection service using Isolation Forest
    """
    _instance: Optional['AnomalyDetector'] = None
    _model: Optional[IsolationForest] = None
    _scaler: Optional[StandardScaler] = None
    _model_loaded: bool = False
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super(AnomalyDetector, cls).__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'AnomalyDetector':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def load_model(self, model_path: Optional[str] = None):
        """Load or initialize the anomaly detection model"""
        model_path = model_path or settings.MODEL_PATH
        
        try:
            # Try to load existing model
            if os.path.exists(model_path):
                logger.info(f"Loading model from {model_path}")
                model_data = joblib.load(model_path)
                
                if isinstance(model_data, dict):
                    self._model = model_data.get('model')
                    self._scaler = model_data.get('scaler')
                else:
                    # Legacy format - assume it's just the model
                    self._model = model_data
                    self._scaler = StandardScaler()
                
                self._model_loaded = True
                logger.info("Model loaded successfully")
            else:
                # Initialize new model if not found
                logger.info("No existing model found. Initializing new model...")
                self._initialize_model()
                self._model_loaded = True
                logger.info("New model initialized successfully")
                
        except Exception as e:
            logger.warning(f"Error loading model: {str(e)}. Initializing new model...")
            self._initialize_model()
            self._model_loaded = True
    
    def _initialize_model(self):
        """Initialize a new Isolation Forest model"""
        self._model = IsolationForest(
            contamination=0.1,  # Expected proportion of anomalies
            random_state=42,
            n_estimators=100
        )
        self._scaler = StandardScaler()
    
    def is_model_loaded(self) -> bool:
        """Check if model is loaded"""
        return self._model_loaded and self._model is not None
    
    def _extract_features(self, transaction: TransactionCreate) -> np.ndarray:
        """Extract features from transaction"""
        features = []
        
        # Amount (most important feature)
        features.append(transaction.amount)
        
        # Merchant (encoded as hash if available)
        merchant_hash = hash(str(transaction.merchant)) % 1000 if transaction.merchant else 0
        features.append(merchant_hash)
        
        # Category (encoded as hash if available)
        category_hash = hash(str(transaction.category)) % 100 if transaction.category else 0
        features.append(category_hash)
        
        # Customer ID (encoded as hash if available)
        customer_hash = hash(str(transaction.customer_id)) % 1000 if transaction.customer_id else 0
        features.append(customer_hash)
        
        return np.array(features).reshape(1, -1)
    
    def detect(self, transaction: TransactionCreate) -> TransactionResponse:
        """
        Detect fraud in a single transaction
        Returns TransactionResponse with fraud detection results
        """
        if not self._model_loaded or self._model is None:
            self.load_model()
        
        # Extract features
        features = self._extract_features(transaction)
        
        # Scale features
        if self._scaler is not None:
            features_scaled = self._scaler.fit_transform(features)
        else:
            features_scaled = features
        
        # Predict anomaly (-1 for anomaly, 1 for normal)
        prediction = self._model.predict(features_scaled)[0]
        
        # Get anomaly score (lower = more anomalous)
        anomaly_score = self._model.score_samples(features_scaled)[0]
        
        # Convert to fraud probability (0-1 scale)
        # Normalize anomaly score to 0-1 range (lower score = higher fraud probability)
        fraud_score = 1 - ((anomaly_score - (-0.5)) / (0.5 - (-0.5)))  # Rough normalization
        fraud_score = max(0.0, min(1.0, fraud_score))  # Clamp to [0, 1]
        
        # Determine if fraud (prediction == -1 means anomaly/fraud)
        is_fraud = prediction == -1 or fraud_score >= settings.FRAUD_THRESHOLD
        
        # Create response
        return TransactionResponse(
            id=hash(str(transaction)) % 1000000,  # Generate a simple ID
            amount=transaction.amount,
            merchant=transaction.merchant,
            category=transaction.category,
            customer_id=transaction.customer_id,
            is_fraud=is_fraud,
            fraud_score=round(fraud_score, 4),
            timestamp=datetime.utcnow()
        )
    
    def detect_batch(self, transactions: List[TransactionCreate]) -> List[TransactionResponse]:
        """
        Detect fraud in a batch of transactions
        """
        if not self._model_loaded or self._model is None:
            self.load_model()
        
        # Extract features for all transactions
        features_list = [self._extract_features(t) for t in transactions]
        features_array = np.vstack(features_list)
        
        # Scale features
        if self._scaler is not None:
            features_scaled = self._scaler.fit_transform(features_array)
        else:
            features_scaled = features_array
        
        # Predict anomalies
        predictions = self._model.predict(features_scaled)
        anomaly_scores = self._model.score_samples(features_scaled)
        
        # Convert to fraud probabilities and create responses
        results = []
        for i, transaction in enumerate(transactions):
            # Normalize anomaly score
            fraud_score = 1 - ((anomaly_scores[i] - (-0.5)) / (0.5 - (-0.5)))
            fraud_score = max(0.0, min(1.0, fraud_score))
            
            is_fraud = predictions[i] == -1 or fraud_score >= settings.FRAUD_THRESHOLD
            
            results.append(TransactionResponse(
                id=hash(str(transaction)) % 1000000,
                amount=transaction.amount,
                merchant=transaction.merchant,
                category=transaction.category,
                customer_id=transaction.customer_id,
                is_fraud=is_fraud,
                fraud_score=round(fraud_score, 4),
                timestamp=datetime.utcnow()
            ))
        
        return results

