from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
import uuid

from app.core.database import supabase
from app.services.file_processor import process_efatura_file
from app.schemas.efatura import EfaturaRecord, EfaturaUploadResponse

router = APIRouter()

@router.post("/upload", response_model=EfaturaUploadResponse)
async def upload_efatura_file(
    file: UploadFile = File(...),
    org_id: str = "550e8400-e29b-41d4-a716-446655440001"  # Default for POC
):
    """Upload and process an e-fatura Excel file"""
    # Validate file extension
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload Excel or CSV file.")
    
    # Check file size (10MB limit)
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")
    
    try:
        # Create file upload record
        upload_record = {
            "org_id": org_id,
            "file_name": file.filename,
            "file_type": "efatura",
            "file_size": len(contents),
            "upload_status": "processing"
        }
        
        upload_result = supabase.table("file_uploads").insert(upload_record).execute()
        upload_id = upload_result.data[0]["id"]
        
        # Process the file
        result = await process_efatura_file(contents, file.filename, upload_id, org_id)
        
        # Update upload status
        supabase.table("file_uploads").update({
            "upload_status": "completed" if result["success"] else "failed",
            "records_count": result["records_processed"],
            "error_message": result.get("error"),
            "completed_at": datetime.utcnow().isoformat()
        }).eq("id", upload_id).execute()
        
        return EfaturaUploadResponse(
            upload_id=upload_id,
            filename=file.filename,
            records_processed=result["records_processed"],
            records_failed=result["records_failed"],
            success=result["success"],
            message=result.get("message", "File processed successfully")
        )
        
    except Exception as e:
        # Update upload status to failed
        if 'upload_id' in locals():
            supabase.table("file_uploads").update({
                "upload_status": "failed",
                "error_message": str(e),
                "completed_at": datetime.utcnow().isoformat()
            }).eq("id", upload_id).execute()
        
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@router.get("/records", response_model=List[EfaturaRecord])
async def get_efatura_records(
    org_id: str = "550e8400-e29b-41d4-a716-446655440001",
    limit: int = 100,
    offset: int = 0,
    matching_status: Optional[str] = None
):
    """Get e-fatura records with optional filtering"""
    query = supabase.table("efatura_records").select("*").eq("org_id", org_id)
    
    if matching_status:
        query = query.eq("matching_status", matching_status)
    
    query = query.order("document_date", desc=True).limit(limit).offset(offset)
    
    result = query.execute()
    return result.data

@router.get("/records/{record_id}", response_model=EfaturaRecord)
async def get_efatura_record(record_id: str):
    """Get a specific e-fatura record"""
    result = supabase.table("efatura_records").select("*").eq("id", record_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="E-fatura record not found")
    
    return result.data[0]

@router.delete("/records/{record_id}")
async def delete_efatura_record(record_id: str):
    """Delete an e-fatura record"""
    # Check if record exists
    result = supabase.table("efatura_records").select("id").eq("id", record_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="E-fatura record not found")
    
    # Delete the record
    supabase.table("efatura_records").delete().eq("id", record_id).execute()
    
    return {"message": "Record deleted successfully"}