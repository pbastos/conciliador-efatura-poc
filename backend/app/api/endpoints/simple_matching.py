"""
Simplified Matching API endpoints using direct SQLite
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.core.database import execute_query, execute_insert, execute_update
from app.services.sqlite_matching_engine import SimplifiedMatchingEngine
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

class ManualMatch(BaseModel):
    efatura_id: int
    bank_movement_id: int

class MatchResponse(BaseModel):
    success: bool
    match_id: int = None
    message: str

@router.post("/auto-match")
async def run_auto_matching():
    """Run automatic matching for all unmatched records"""
    
    engine = SimplifiedMatchingEngine()
    results = engine.auto_match_all()
    
    return results

@router.get("/suggestions/{efatura_id}")
async def get_match_suggestions(efatura_id: int):
    """Get potential matches for a specific e-fatura record"""
    
    engine = SimplifiedMatchingEngine()
    
    # Get the e-fatura record
    efatura = execute_query(
        "SELECT * FROM efatura_records WHERE id = ?", 
        (efatura_id,)
    )
    
    if not efatura:
        raise HTTPException(404, "E-fatura record not found")
    
    efatura = efatura[0]
    
    # Get potential matches
    suggestions = engine.find_potential_matches(efatura_id)
    
    # Calculate scores for each suggestion
    for suggestion in suggestions:
        suggestion['confidence_score'] = engine.calculate_match_score(efatura, suggestion)
    
    return {
        "efatura": efatura,
        "suggestions": suggestions
    }

@router.post("/manual-match")
async def create_manual_match(match: ManualMatch):
    """Create a manual match between e-fatura and bank movement"""
    
    # Verify both records exist and are unmatched
    efatura = execute_query(
        "SELECT * FROM efatura_records WHERE id = ? AND status = 'unmatched'",
        (match.efatura_id,)
    )
    
    bank_movement = execute_query(
        "SELECT * FROM bank_movements WHERE id = ? AND status = 'unmatched'",
        (match.bank_movement_id,)
    )
    
    if not efatura:
        raise HTTPException(404, "E-fatura record not found or already matched")
    
    if not bank_movement:
        raise HTTPException(404, "Bank movement not found or already matched")
    
    # Calculate confidence score
    engine = SimplifiedMatchingEngine()
    confidence_score = engine.calculate_match_score(efatura[0], bank_movement[0])
    
    # Create match
    match_id = engine.create_match(match.efatura_id, match.bank_movement_id, confidence_score)
    
    return MatchResponse(
        success=True,
        match_id=match_id,
        message=f"Match created successfully with confidence score: {confidence_score}"
    )

@router.get("/matches")
async def get_all_matches(limit: int = 100, offset: int = 0):
    """Get all matches with details"""
    
    matches = execute_query("""
        SELECT 
            m.*,
            e.document_number,
            e.document_date,
            e.supplier_name,
            e.total_amount as efatura_amount,
            b.movement_date,
            b.description as bank_description,
            b.amount as bank_amount
        FROM matches m
        JOIN efatura_records e ON m.efatura_id = e.id
        JOIN bank_movements b ON m.bank_movement_id = b.id
        ORDER BY m.created_at DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))
    
    total = execute_query("SELECT COUNT(*) as total FROM matches")[0]['total']
    
    return {
        "matches": matches,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@router.delete("/match/{match_id}")
async def delete_match(match_id: int):
    """Delete a match and reset the status of both records"""
    
    # Get match details
    match = execute_query(
        "SELECT * FROM matches WHERE id = ?",
        (match_id,)
    )
    
    if not match:
        raise HTTPException(404, "Match not found")
    
    match = match[0]
    
    # Update statuses back to unmatched
    execute_update(
        "UPDATE efatura_records SET status = 'unmatched' WHERE id = ?",
        (match['efatura_id'],)
    )
    
    execute_update(
        "UPDATE bank_movements SET status = 'unmatched' WHERE id = ?",
        (match['bank_movement_id'],)
    )
    
    # Delete the match
    execute_update(
        "DELETE FROM matches WHERE id = ?",
        (match_id,)
    )
    
    return {"message": "Match deleted successfully"}

@router.get("/summary")
async def get_matching_summary():
    """Get overall matching summary"""
    
    engine = SimplifiedMatchingEngine()
    summary = engine.get_match_summary()
    
    # Add percentage calculations
    if summary['total_efaturas'] > 0:
        summary['efatura_match_rate'] = round(
            (summary['matched_efaturas'] / summary['total_efaturas']) * 100, 2
        )
    else:
        summary['efatura_match_rate'] = 0
    
    if summary['total_bank_movements'] > 0:
        summary['bank_match_rate'] = round(
            (summary['matched_bank_movements'] / summary['total_bank_movements']) * 100, 2
        )
    else:
        summary['bank_match_rate'] = 0
    
    return summary