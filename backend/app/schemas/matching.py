from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal

class MatchingParameters(BaseModel):
    date_tolerance_days: int = Field(3, ge=0, le=30)
    amount_tolerance_percent: float = Field(0.01, ge=0, le=0.1)
    description_min_similarity: float = Field(0.7, ge=0, le=1)
    use_reference_matching: bool = True
    batch_size: int = Field(100, ge=10, le=1000)

class MatchingCriteria(BaseModel):
    date_matched: bool
    amount_matched: bool
    description_matched: bool
    reference_matched: bool
    date_difference_days: int
    amount_difference: Decimal
    description_similarity: float

class MatchingResultBase(BaseModel):
    efatura_id: str
    bank_movement_id: str
    confidence_score: float = Field(..., ge=0, le=1)
    matching_method: str
    date_difference: int
    amount_difference: Decimal
    matching_criteria: Dict[str, Any]
    matched_fields: List[str]

class MatchingResultCreate(MatchingResultBase):
    org_id: str

class MatchingResult(MatchingResultBase):
    id: str
    org_id: str
    status: str = "proposed"
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    rejected_by: Optional[str] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    # Nested data when joined
    efatura_records: Optional[Dict[str, Any]] = None
    bank_movements: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

class MatchingSession(BaseModel):
    id: str
    org_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_efatura_records: int
    total_bank_movements: int
    matched_count: int = 0
    unmatched_efatura_count: int = 0
    unmatched_bank_count: int = 0
    parameters: Dict[str, Any]
    created_by: Optional[str] = None
    status: str = "running"
    
    class Config:
        from_attributes = True

class MatchingSessionResponse(BaseModel):
    session_id: str
    status: str
    message: str