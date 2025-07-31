"""
Simplified Bank movements API endpoints using direct SQLite
"""
from fastapi import APIRouter, File, UploadFile, HTTPException
from typing import List, Dict, Any
import os
import shutil
from app.core.config import settings
from app.core.database import execute_query
from app.services.sqlite_file_processor import SimplifiedFileProcessor

router = APIRouter()

@router.post("/upload")
async def upload_bank_file(file: UploadFile = File(...)):
    """Upload and process bank movements Excel file"""
    
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
    result = SimplifiedFileProcessor.process_bank_file(file_path, file.filename)
    
    if not result['success']:
        raise HTTPException(400, f"Error processing file: {result['error']}")
    
    return result

@router.get("/movements")
async def get_bank_movements(
    limit: int = 100,
    offset: int = 0,
    status: str = None,
    movement_type: str = None
):
    """Get bank movements with pagination"""
    
    query = "SELECT * FROM bank_movements WHERE 1=1"
    params = []
    
    if status:
        query += " AND status = ?"
        params.append(status)
    
    if movement_type:
        query += " AND movement_type = ?"
        params.append(movement_type)
    
    query += " ORDER BY movement_date DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    movements = execute_query(query, tuple(params))
    
    # Get total count
    count_query = "SELECT COUNT(*) as total FROM bank_movements WHERE 1=1"
    count_params = []
    
    if status:
        count_query += " AND status = ?"
        count_params.append(status)
    
    if movement_type:
        count_query += " AND movement_type = ?"
        count_params.append(movement_type)
    
    total = execute_query(count_query, tuple(count_params) if count_params else None)[0]['total']
    
    return {
        "movements": movements,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@router.get("/summary")
async def get_bank_summary():
    """Get summary statistics for bank movements"""
    
    summary = execute_query("""
        SELECT 
            COUNT(*) as total_movements,
            COUNT(DISTINCT upload_id) as total_uploads,
            SUM(CASE WHEN status = 'matched' THEN 1 ELSE 0 END) as matched_movements,
            SUM(CASE WHEN status = 'unmatched' THEN 1 ELSE 0 END) as unmatched_movements,
            SUM(CASE WHEN movement_type = 'credit' THEN amount ELSE 0 END) as total_credits,
            SUM(CASE WHEN movement_type = 'debit' THEN ABS(amount) ELSE 0 END) as total_debits,
            MIN(movement_date) as oldest_movement,
            MAX(movement_date) as newest_movement
        FROM bank_movements
    """)[0]
    
    return summary

@router.get("/unmatched")
async def get_unmatched_movements(limit: int = 50):
    """Get unmatched bank movements that need attention"""
    
    movements = execute_query("""
        SELECT * FROM bank_movements 
        WHERE status = 'unmatched'
        ORDER BY movement_date DESC
        LIMIT ?
    """, (limit,))
    
    return movements