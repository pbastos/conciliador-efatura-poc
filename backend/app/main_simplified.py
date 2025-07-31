from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
import os

from app.database import init_database, get_db_cursor, update_match_status
from app.file_processor import process_efatura_file, process_bank_file
from app.matching import run_automatic_matching, get_match_suggestions

# Initialize FastAPI app
app = FastAPI(
    title="Conciliador E-fatura POC",
    description="Simple reconciliation tool for e-fatura and bank movements",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_database()
    print("Database initialized")

# Health check
@app.get("/")
def read_root():
    return {"message": "Conciliador E-fatura API is running"}

# Upload e-fatura file
@app.post("/api/v1/efatura/upload")
async def upload_efatura(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="Invalid file format")
    
    contents = await file.read()
    
    # Create upload batch
    with get_db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO upload_batches (filename, file_type, status)
            VALUES (?, 'efatura', 'processing')
        """, (file.filename,))
        batch_id = cursor.lastrowid
    
    # Process file
    result = process_efatura_file(contents, file.filename, batch_id)
    
    # Update batch status
    with get_db_cursor() as cursor:
        cursor.execute("""
            UPDATE upload_batches 
            SET status = ?, processed_records = ?
            WHERE id = ?
        """, ('completed' if result['success'] else 'failed', 
              result.get('records_processed', 0), batch_id))
    
    return result

# Upload bank movements file
@app.post("/api/v1/bank/upload")
async def upload_bank(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="Invalid file format")
    
    contents = await file.read()
    
    # Create upload batch
    with get_db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO upload_batches (filename, file_type, status)
            VALUES (?, 'bank', 'processing')
        """, (file.filename,))
        batch_id = cursor.lastrowid
    
    # Process file
    result = process_bank_file(contents, file.filename, batch_id)
    
    # Update batch status
    with get_db_cursor() as cursor:
        cursor.execute("""
            UPDATE upload_batches 
            SET status = ?, processed_records = ?
            WHERE id = ?
        """, ('completed' if result['success'] else 'failed', 
              result.get('records_processed', 0), batch_id))
    
    return result

# Run automatic matching
@app.post("/api/v1/matching/auto-match")
async def auto_match(min_confidence: float = 0.5):
    result = run_automatic_matching(min_confidence)
    return result

# Get matching suggestions
@app.get("/api/v1/matching/suggestions/{record_id}")
async def get_suggestions(record_id: int, record_type: str):
    if record_type == "efatura":
        suggestions = get_match_suggestions(efatura_id=record_id)
    elif record_type == "bank":
        suggestions = get_match_suggestions(bank_movement_id=record_id)
    else:
        raise HTTPException(status_code=400, detail="Invalid record type")
    
    return suggestions

# Get all matches
@app.get("/api/v1/matching/matches")
async def get_matches(status: Optional[str] = None):
    with get_db_cursor() as cursor:
        query = """
            SELECT 
                m.id,
                m.confidence_score,
                m.match_type,
                m.status,
                m.created_at,
                e.id as efatura_id,
                e.issuer,
                e.invoice,
                e.issue_date,
                e.total as efatura_total,
                b.id as bank_id,
                b.movement_date,
                b.description,
                b.amount as bank_amount
            FROM matching_results m
            JOIN efatura e ON m.efatura_id = e.id
            JOIN bank_movements b ON m.bank_movement_id = b.id
        """
        
        if status:
            query += " WHERE m.status = ?"
            cursor.execute(query, (status,))
        else:
            cursor.execute(query)
        
        matches = [dict(row) for row in cursor.fetchall()]
    
    return matches

# Update match status
@app.put("/api/v1/matching/matches/{match_id}/status")
async def update_match(match_id: int, status: str):
    if status not in ['confirmed', 'rejected', 'proposed']:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    success = update_match_status(match_id, status)
    if not success:
        raise HTTPException(status_code=404, detail="Match not found")
    
    return {"message": f"Match status updated to {status}"}

# Get summary statistics
@app.get("/api/v1/matching/summary")
async def get_summary():
    with get_db_cursor() as cursor:
        # Total records
        cursor.execute("SELECT COUNT(*) as count FROM efatura")
        efatura_total = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM bank_movements")
        bank_total = cursor.fetchone()['count']
        
        # Matched records
        cursor.execute("""
            SELECT COUNT(DISTINCT efatura_id) as count 
            FROM matching_results 
            WHERE status != 'rejected'
        """)
        efatura_matched = cursor.fetchone()['count']
        
        cursor.execute("""
            SELECT COUNT(DISTINCT bank_movement_id) as count 
            FROM matching_results 
            WHERE status != 'rejected'
        """)
        bank_matched = cursor.fetchone()['count']
        
        # Match status breakdown
        cursor.execute("""
            SELECT status, COUNT(*) as count 
            FROM matching_results 
            GROUP BY status
        """)
        status_breakdown = {row['status']: row['count'] for row in cursor.fetchall()}
    
    return {
        "efatura": {
            "total": efatura_total,
            "matched": efatura_matched,
            "unmatched": efatura_total - efatura_matched
        },
        "bank_movements": {
            "total": bank_total,
            "matched": bank_matched,
            "unmatched": bank_total - bank_matched
        },
        "matches": status_breakdown
    }

# Get unmatched records
@app.get("/api/v1/records/unmatched")
async def get_unmatched(record_type: str):
    if record_type == "efatura":
        from app.database import get_unmatched_efatura
        return get_unmatched_efatura()
    elif record_type == "bank":
        from app.database import get_unmatched_bank_movements
        return get_unmatched_bank_movements()
    else:
        raise HTTPException(status_code=400, detail="Invalid record type")