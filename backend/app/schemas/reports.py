from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MatchingSummary(BaseModel):
    total_efatura_records: int
    total_bank_movements: int
    matched_efatura_records: int
    matched_bank_movements: int
    unmatched_efatura_records: int
    unmatched_bank_movements: int
    confirmed_matches: int
    proposed_matches: int
    rejected_matches: int
    efatura_match_rate: float
    bank_match_rate: float
    
    class Config:
        from_attributes = True

class UploadHistory(BaseModel):
    id: str
    org_id: str
    file_name: str
    file_type: str
    file_size: Optional[int] = None
    records_count: int = 0
    upload_status: str
    error_message: Optional[str] = None
    uploaded_by: Optional[str] = None
    uploaded_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True