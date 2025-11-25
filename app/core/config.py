from typing import Optional
import os


class Settings:
    """Application settings"""
    
    # API Settings
    APP_NAME: str = "FraudShield API"
    VERSION: str = "1.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Database Settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./fraudshield.db"
    )
    
    # Model Settings
    MODEL_PATH: Optional[str] = os.getenv(
        "MODEL_PATH",
        "models/isolation_forest_model.joblib"
    )
    
    # Feature Settings
    FRAUD_THRESHOLD: float = float(os.getenv("FRAUD_THRESHOLD", "0.5"))


settings = Settings()

