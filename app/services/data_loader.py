import pandas as pd
from typing import Optional, List
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class DataLoader:
    """
    Service for loading transaction data from various sources
    """
    _instance: Optional['DataLoader'] = None
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super(DataLoader, cls).__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'DataLoader':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def load_from_csv(self, file_path: str) -> pd.DataFrame:
        """
        Load transaction data from CSV file
        """
        try:
            df = pd.read_csv(file_path)
            logger.info(f"Loaded {len(df)} transactions from {file_path}")
            return df
        except Exception as e:
            logger.error(f"Error loading CSV file: {str(e)}")
            raise
    
    def load_from_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate and return dataframe
        """
        # Validate required columns
        required_columns = ['amount']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
        
        return df

