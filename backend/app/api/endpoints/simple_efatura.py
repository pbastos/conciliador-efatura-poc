"""
Simplified E-fatura API endpoints using direct SQLite
"""
from fastapi import APIRouter, File, UploadFile, HTTPException
from typing import List, Dict, Any
import os
import shutil
from app.core.config import settings
from app.core.database import execute_query, init_db
from app.services.sqlite_file_processor import SimplifiedFileProcessor

router = APIRouter()

# Initialize database on startup
init_db()

@router.post("/upload")
async def upload_efatura_file(file: UploadFile = File(...)):
    """Upload and process e-fatura Excel file"""
    
    # Validate file extension
    if not any(file.filename.endswith(ext) for ext in settings.ALLOWED_EXTENSIONS):
        raise HTTPException(400, f"Invalid file type. Allowed: {settings.ALLOWED_EXTENSIONS}")
    
    # Create upload directory if it doesn't exist
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Save uploaded file temporarily
    file_path = os.path.join(settings.UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Process file
    result = SimplifiedFileProcessor.process_efatura_file(file_path, file.filename)
    
    if not result['success']:
        raise HTTPException(400, f"Error processing file: {result['error']}")
    
    return result

@router.get("/records")
async def get_efatura_records(
    limit: int = 100,
    offset: int = 0,
    status: str = None
):
    """Get e-fatura records with pagination"""
    
    query = "SELECT * FROM efatura_records"
    params = []
    
    if status:
        query += " WHERE status = ?"
        params.append(status)
    
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    records = execute_query(query, tuple(params))
    
    # Get total count
    count_query = "SELECT COUNT(*) as total FROM efatura_records"
    if status:
        count_query += " WHERE status = ?"
        total = execute_query(count_query, (status,))[0]['total']
    else:
        total = execute_query(count_query)[0]['total']
    
    return {
        "records": records,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@router.get("/summary")
async def get_efatura_summary():
    """Get summary statistics for e-fatura records"""
    
    summary = execute_query("""
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT upload_id) as total_uploads,
            SUM(CASE WHEN status = 'matched' THEN 1 ELSE 0 END) as matched_records,
            SUM(CASE WHEN status = 'unmatched' THEN 1 ELSE 0 END) as unmatched_records,
            SUM(total_amount) as total_amount,
            AVG(total_amount) as average_amount,
            MIN(document_date) as oldest_document,
            MAX(document_date) as newest_document
        FROM efatura_records
    """)[0]
    
    return summary

@router.delete("/upload/{upload_id}")
async def delete_upload(upload_id: str):
    """Delete all records from a specific upload"""
    
    # Delete from efatura_records
    execute_query("DELETE FROM efatura_records WHERE upload_id = ?", (upload_id,))
    
    # Delete from uploads table
    execute_query("DELETE FROM uploads WHERE id = ?", (upload_id,))
    
    return {"message": f"Upload {upload_id} deleted successfully"}