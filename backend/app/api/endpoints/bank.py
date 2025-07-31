from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List, Optional
from datetime import datetime

from app.core.database import supabase
from app.services.file_processor import process_bank_file
from app.schemas.bank import BankMovement, BankUploadResponse

router = APIRouter()

@router.post("/upload", response_model=BankUploadResponse)
async def upload_bank_file(
    file: UploadFile = File(...),
    org_id: str = "550e8400-e29b-41d4-a716-446655440001"  # Default for POC
):
    """Upload and process a bank movements Excel file"""
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
            "file_type": "bank",
            "file_size": len(contents),
            "upload_status": "processing"
        }
        
        upload_result = supabase.table("file_uploads").insert(upload_record).execute()
        upload_id = upload_result.data[0]["id"]
        
        # Process the file
        result = await process_bank_file(contents, file.filename, upload_id, org_id)
        
        # Update upload status
        supabase.table("file_uploads").update({
            "upload_status": "completed" if result["success"] else "failed",
            "records_count": result["records_processed"],
            "error_message": result.get("error"),
            "completed_at": datetime.utcnow().isoformat()
        }).eq("id", upload_id).execute()
        
        return BankUploadResponse(
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

@router.get("/movements", response_model=List[BankMovement])
async def get_bank_movements(
    org_id: str = "550e8400-e29b-41d4-a716-446655440001",
    limit: int = 100,
    offset: int = 0,
    matching_status: Optional[str] = None
):
    """Get bank movements with optional filtering"""
    query = supabase.table("bank_movements").select("*").eq("org_id", org_id)
    
    if matching_status:
        query = query.eq("matching_status", matching_status)
    
    query = query.order("movement_date", desc=True).limit(limit).offset(offset)
    
    result = query.execute()
    return result.data

@router.get("/movements/{movement_id}", response_model=BankMovement)
async def get_bank_movement(movement_id: str):
    """Get a specific bank movement"""
    result = supabase.table("bank_movements").select("*").eq("id", movement_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Bank movement not found")
    
    return result.data[0]

@router.delete("/movements/{movement_id}")
async def delete_bank_movement(movement_id: str):
    """Delete a bank movement"""
    # Check if movement exists
    result = supabase.table("bank_movements").select("id").eq("id", movement_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Bank movement not found")
    
    # Delete the movement
    supabase.table("bank_movements").delete().eq("id", movement_id).execute()
    
    return {"message": "Movement deleted successfully"}