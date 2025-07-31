from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal
import uuid

class EfaturaBase(BaseModel):
    document_number: Optional[str] = None
    document_date: date
    supplier_nif: Optional[str] = None
    supplier_name: Optional[str] = None
    total_amount: Decimal = Field(..., decimal_places=2)
    tax_amount: Optional[Decimal] = Field(None, decimal_places=2)
    taxable_base: Optional[Decimal] = Field(None, decimal_places=2)
    description: Optional[str] = None
    document_type: Optional[str] = None

class EfaturaCreate(EfaturaBase):
    org_id: str
    file_upload_id: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None

class EfaturaRecord(EfaturaBase):
    id: str
    org_id: str
    file_upload_id: Optional[str] = None
    matching_status: str = "unmatched"
    raw_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class EfaturaUploadResponse(BaseModel):
    upload_id: str
    filename: str
    records_processed: int
    records_failed: int
    success: bool
    message: str