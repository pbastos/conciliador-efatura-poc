from pydantic_settings import BaseSettings
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Conciliador E-fatura POC"
    VERSION: str = "0.1.0"
    DEBUG: bool = True
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    # SQLite Database
    DATABASE_NAME: str = "conciliador.db"
    DATABASE_PATH: str = os.path.join(os.path.dirname(__file__), "..", "..", DATABASE_NAME)
    
    # File Upload
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: List[str] = [".xlsx", ".xls"]
    UPLOAD_DIR: str = "uploads"
    
    # Matching Configuration
    DATE_TOLERANCE_DAYS: int = 3
    AMOUNT_TOLERANCE_PERCENT: float = 0.01
    MIN_CONFIDENCE_SCORE: float = 0.5
    AUTO_MATCH_THRESHOLD: float = 0.8
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()