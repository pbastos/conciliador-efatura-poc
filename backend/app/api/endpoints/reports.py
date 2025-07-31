from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import datetime
import io

from app.core.database import supabase
from app.services.report_generator import generate_matching_report, export_to_excel
from app.schemas.reports import MatchingSummary

router = APIRouter()

@router.get("/matching-summary", response_model=MatchingSummary)
async def get_matching_summary(
    org_id: str = "550e8400-e29b-41d4-a716-446655440001",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """Get summary statistics for matching"""
    try:
        # Get total counts
        efatura_total = supabase.table("efatura_records")\
            .select("id", count="exact")\
            .eq("org_id", org_id)\
            .execute()
        
        bank_total = supabase.table("bank_movements")\
            .select("id", count="exact")\
            .eq("org_id", org_id)\
            .execute()
        
        # Get matched counts
        efatura_matched = supabase.table("efatura_records")\
            .select("id", count="exact")\
            .eq("org_id", org_id)\
            .in_("matching_status", ["matched", "confirmed"])\
            .execute()
        
        bank_matched = supabase.table("bank_movements")\
            .select("id", count="exact")\
            .eq("org_id", org_id)\
            .in_("matching_status", ["matched", "confirmed"])\
            .execute()
        
        # Get matching results by status
        confirmed_matches = supabase.table("matching_results")\
            .select("id", count="exact")\
            .eq("org_id", org_id)\
            .eq("status", "confirmed")\
            .execute()
        
        proposed_matches = supabase.table("matching_results")\
            .select("id", count="exact")\
            .eq("org_id", org_id)\
            .eq("status", "proposed")\
            .execute()
        
        rejected_matches = supabase.table("matching_results")\
            .select("id", count="exact")\
            .eq("org_id", org_id)\
            .eq("status", "rejected")\
            .execute()
        
        # Calculate percentages
        efatura_match_rate = (efatura_matched.count / efatura_total.count * 100) if efatura_total.count > 0 else 0
        bank_match_rate = (bank_matched.count / bank_total.count * 100) if bank_total.count > 0 else 0
        
        return MatchingSummary(
            total_efatura_records=efatura_total.count,
            total_bank_movements=bank_total.count,
            matched_efatura_records=efatura_matched.count,
            matched_bank_movements=bank_matched.count,
            unmatched_efatura_records=efatura_total.count - efatura_matched.count,
            unmatched_bank_movements=bank_total.count - bank_matched.count,
            confirmed_matches=confirmed_matches.count,
            proposed_matches=proposed_matches.count,
            rejected_matches=rejected_matches.count,
            efatura_match_rate=round(efatura_match_rate, 2),
            bank_match_rate=round(bank_match_rate, 2)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")

@router.get("/export/excel")
async def export_matching_report(
    org_id: str = "550e8400-e29b-41d4-a716-446655440001",
    include_unmatched: bool = True,
    status_filter: Optional[str] = None
):
    """Export matching results to Excel"""
    try:
        # Get matched records
        query = supabase.table("matching_results")\
            .select("*, efatura_records!inner(*), bank_movements!inner(*)")\
            .eq("org_id", org_id)
        
        if status_filter:
            query = query.eq("status", status_filter)
        
        matched_results = query.execute()
        
        unmatched_efatura = []
        unmatched_bank = []
        
        if include_unmatched:
            # Get unmatched e-fatura records
            unmatched_efatura = supabase.table("efatura_records")\
                .select("*")\
                .eq("org_id", org_id)\
                .eq("matching_status", "unmatched")\
                .execute().data
            
            # Get unmatched bank movements
            unmatched_bank = supabase.table("bank_movements")\
                .select("*")\
                .eq("org_id", org_id)\
                .eq("matching_status", "unmatched")\
                .execute().data
        
        # Generate Excel file
        excel_buffer = export_to_excel(
            matched_results.data,
            unmatched_efatura,
            unmatched_bank
        )
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(excel_buffer),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=conciliation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating Excel report: {str(e)}")

@router.get("/upload-history")
async def get_upload_history(
    org_id: str = "550e8400-e29b-41d4-a716-446655440001",
    file_type: Optional[str] = None,
    limit: int = 20
):
    """Get file upload history"""
    query = supabase.table("file_uploads")\
        .select("*")\
        .eq("org_id", org_id)\
        .order("uploaded_at", desc=True)\
        .limit(limit)
    
    if file_type:
        query = query.eq("file_type", file_type)
    
    result = query.execute()
    return result.data