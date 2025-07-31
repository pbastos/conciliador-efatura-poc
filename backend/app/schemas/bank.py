from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal

class BankMovementBase(BaseModel):
    movement_date: date
    value_date: Optional[date] = None
    description: Optional[str] = None
    amount: Decimal = Field(..., decimal_places=2)
    balance: Optional[Decimal] = Field(None, decimal_places=2)
    reference: Optional[str] = None
    movement_type: Optional[str] = None

class BankMovementCreate(BankMovementBase):
    org_id: str
    file_upload_id: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None

class BankMovement(BankMovementBase):
    id: str
    org_id: str
    file_upload_id: Optional[str] = None
    matching_status: str = "unmatched"
    raw_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class BankUploadResponse(BaseModel):
    upload_id: str
    filename: str
    records_processed: int
    records_failed: int
    success: bool
    message: str