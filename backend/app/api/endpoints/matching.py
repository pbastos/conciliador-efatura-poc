from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional, Dict
from datetime import datetime
import uuid

from app.core.database import supabase
from app.services.matching_engine import run_matching_process
from app.schemas.matching import (
    MatchingSession, 
    MatchingResult, 
    MatchingParameters,
    MatchingSessionResponse
)

router = APIRouter()

@router.post("/start", response_model=MatchingSessionResponse)
async def start_matching_session(
    background_tasks: BackgroundTasks,
    params: MatchingParameters,
    org_id: str = "550e8400-e29b-41d4-a716-446655440001"
):
    """Start a new matching session"""
    try:
        # Count unmatched records
        efatura_count = supabase.table("efatura_records")\
            .select("id", count="exact")\
            .eq("org_id", org_id)\
            .eq("matching_status", "unmatched")\
            .execute()
        
        bank_count = supabase.table("bank_movements")\
            .select("id", count="exact")\
            .eq("org_id", org_id)\
            .eq("matching_status", "unmatched")\
            .execute()
        
        # Create matching session
        session_data = {
            "org_id": org_id,
            "total_efatura_records": efatura_count.count,
            "total_bank_movements": bank_count.count,
            "parameters": params.dict(),
            "status": "running"
        }
        
        session_result = supabase.table("matching_sessions").insert(session_data).execute()
        session_id = session_result.data[0]["id"]
        
        # Run matching process in background
        background_tasks.add_task(
            run_matching_process,
            session_id,
            org_id,
            params
        )
        
        return MatchingSessionResponse(
            session_id=session_id,
            status="running",
            message=f"Matching session started. Processing {efatura_count.count} e-fatura records and {bank_count.count} bank movements."
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting matching session: {str(e)}")

@router.get("/sessions", response_model=List[MatchingSession])
async def get_matching_sessions(
    org_id: str = "550e8400-e29b-41d4-a716-446655440001",
    limit: int = 10
):
    """Get list of matching sessions"""
    result = supabase.table("matching_sessions")\
        .select("*")\
        .eq("org_id", org_id)\
        .order("started_at", desc=True)\
        .limit(limit)\
        .execute()
    
    return result.data

@router.get("/sessions/{session_id}", response_model=MatchingSession)
async def get_matching_session(session_id: str):
    """Get details of a specific matching session"""
    result = supabase.table("matching_sessions")\
        .select("*")\
        .eq("id", session_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Matching session not found")
    
    return result.data[0]

@router.get("/results", response_model=List[MatchingResult])
async def get_matching_results(
    org_id: str = "550e8400-e29b-41d4-a716-446655440001",
    status: Optional[str] = None,
    min_confidence: Optional[float] = None,
    limit: int = 100,
    offset: int = 0
):
    """Get matching results with optional filtering"""
    query = supabase.table("matching_results")\
        .select("*, efatura_records!inner(*), bank_movements!inner(*)")\
        .eq("org_id", org_id)
    
    if status:
        query = query.eq("status", status)
    
    if min_confidence is not None:
        query = query.gte("confidence_score", min_confidence)
    
    query = query.order("confidence_score", desc=True).limit(limit).offset(offset)
    
    result = query.execute()
    return result.data

@router.put("/results/{result_id}/confirm")
async def confirm_matching_result(result_id: str):
    """Confirm a matching result"""
    # Check if result exists
    result = supabase.table("matching_results")\
        .select("*, efatura_id, bank_movement_id")\
        .eq("id", result_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Matching result not found")
    
    match_data = result.data[0]
    
    # Update matching result
    supabase.table("matching_results").update({
        "status": "confirmed",
        "confirmed_at": datetime.utcnow().isoformat()
    }).eq("id", result_id).execute()
    
    # Update e-fatura record status
    supabase.table("efatura_records").update({
        "matching_status": "confirmed"
    }).eq("id", match_data["efatura_id"]).execute()
    
    # Update bank movement status
    supabase.table("bank_movements").update({
        "matching_status": "confirmed"
    }).eq("id", match_data["bank_movement_id"]).execute()
    
    return {"message": "Match confirmed successfully"}

@router.put("/results/{result_id}/reject")
async def reject_matching_result(
    result_id: str,
    reason: Optional[str] = None
):
    """Reject a matching result"""
    # Check if result exists
    result = supabase.table("matching_results")\
        .select("*, efatura_id, bank_movement_id")\
        .eq("id", result_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Matching result not found")
    
    match_data = result.data[0]
    
    # Update matching result
    update_data = {
        "status": "rejected",
        "rejected_at": datetime.utcnow().isoformat()
    }
    if reason:
        update_data["rejection_reason"] = reason
    
    supabase.table("matching_results").update(update_data).eq("id", result_id).execute()
    
    # Reset e-fatura record status
    supabase.table("efatura_records").update({
        "matching_status": "unmatched"
    }).eq("id", match_data["efatura_id"]).execute()
    
    # Reset bank movement status
    supabase.table("bank_movements").update({
        "matching_status": "unmatched"
    }).eq("id", match_data["bank_movement_id"]).execute()
    
    return {"message": "Match rejected successfully"}