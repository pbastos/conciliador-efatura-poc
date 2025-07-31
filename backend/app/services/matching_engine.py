from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Tuple
from thefuzz import fuzz
import traceback

from app.core.database import supabase
from app.schemas.matching import MatchingParameters

async def run_matching_process(
    session_id: str,
    org_id: str,
    params: MatchingParameters
) -> None:
    """Run the matching process for a session"""
    try:
        # Get unmatched e-fatura records
        efatura_records = supabase.table("efatura_records")\
            .select("*")\
            .eq("org_id", org_id)\
            .eq("matching_status", "unmatched")\
            .execute().data
        
        # Get unmatched bank movements
        bank_movements = supabase.table("bank_movements")\
            .select("*")\
            .eq("org_id", org_id)\
            .eq("matching_status", "unmatched")\
            .execute().data
        
        # Process matches
        matches_created = 0
        
        for efatura in efatura_records:
            best_match = None
            best_score = 0
            
            for bank in bank_movements:
                # Calculate match score
                score, criteria = calculate_match_score(efatura, bank, params)
                
                if score > best_score and score >= 0.5:  # Minimum threshold
                    best_match = (bank, score, criteria)
                    best_score = score
            
            if best_match:
                bank, score, criteria = best_match
                
                # Create matching result
                match_data = {
                    "org_id": org_id,
                    "efatura_id": efatura["id"],
                    "bank_movement_id": bank["id"],
                    "confidence_score": score,
                    "matching_method": "fuzzy" if score < 0.95 else "exact",
                    "date_difference": criteria["date_difference_days"],
                    "amount_difference": str(criteria["amount_difference"]),
                    "matching_criteria": criteria,
                    "matched_fields": get_matched_fields(criteria),
                    "status": "proposed"
                }
                
                supabase.table("matching_results").insert(match_data).execute()
                
                # Update records status
                supabase.table("efatura_records").update({
                    "matching_status": "matched"
                }).eq("id", efatura["id"]).execute()
                
                supabase.table("bank_movements").update({
                    "matching_status": "matched"
                }).eq("id", bank["id"]).execute()
                
                # Remove matched bank movement from list
                bank_movements.remove(bank)
                matches_created += 1
        
        # Update session
        session_update = {
            "completed_at": datetime.utcnow().isoformat(),
            "matched_count": matches_created,
            "unmatched_efatura_count": len(efatura_records) - matches_created,
            "unmatched_bank_count": len(bank_movements),
            "status": "completed"
        }
        
        supabase.table("matching_sessions").update(session_update)\
            .eq("id", session_id).execute()
        
    except Exception as e:
        print(f"Error in matching process: {str(e)}")
        traceback.print_exc()
        
        # Update session with error
        supabase.table("matching_sessions").update({
            "status": "failed",
            "completed_at": datetime.utcnow().isoformat()
        }).eq("id", session_id).execute()

def calculate_match_score(
    efatura: Dict[str, Any],
    bank: Dict[str, Any],
    params: MatchingParameters
) -> Tuple[float, Dict[str, Any]]:
    """Calculate match score between e-fatura record and bank movement"""
    score = 0.0
    max_score = 0.0
    
    # Parse dates
    efatura_date = datetime.fromisoformat(efatura["document_date"])
    bank_date = datetime.fromisoformat(bank["movement_date"])
    
    # Date matching (weight: 0.3)
    date_diff = abs((efatura_date - bank_date).days)
    date_matched = date_diff <= params.date_tolerance_days
    max_score += 0.3
    
    if date_matched:
        # Linear score based on closeness
        date_score = 0.3 * (1 - (date_diff / params.date_tolerance_days))
        score += date_score
    
    # Amount matching (weight: 0.4)
    efatura_amount = Decimal(str(efatura["total_amount"]))
    bank_amount = abs(Decimal(str(bank["amount"])))  # Bank amounts are negative for payments
    amount_diff = abs(efatura_amount - bank_amount)
    amount_tolerance = efatura_amount * Decimal(str(params.amount_tolerance_percent))
    amount_matched = amount_diff <= amount_tolerance
    max_score += 0.4
    
    if amount_matched:
        # Exact match gets full score
        if amount_diff == 0:
            score += 0.4
        else:
            # Linear score based on closeness
            amount_score = 0.4 * (1 - (float(amount_diff) / float(amount_tolerance)))
            score += amount_score
    
    # Description matching (weight: 0.2)
    description_similarity = 0.0
    if efatura.get("supplier_name") and bank.get("description"):
        # Fuzzy string matching
        similarity1 = fuzz.partial_ratio(
            efatura["supplier_name"].lower(),
            bank["description"].lower()
        ) / 100.0
        
        # Also check NIF in description
        if efatura.get("supplier_nif"):
            similarity2 = 1.0 if efatura["supplier_nif"] in bank["description"] else 0.0
            description_similarity = max(similarity1, similarity2)
        else:
            description_similarity = similarity1
    
    description_matched = description_similarity >= params.description_min_similarity
    max_score += 0.2
    
    if description_matched:
        score += 0.2 * description_similarity
    
    # Reference matching (weight: 0.1)
    reference_matched = False
    if params.use_reference_matching and efatura.get("document_number") and bank.get("reference"):
        # Check if document number appears in reference
        reference_matched = efatura["document_number"] in bank["reference"]
    
    max_score += 0.1
    if reference_matched:
        score += 0.1
    
    # Normalize score
    final_score = score / max_score if max_score > 0 else 0
    
    criteria = {
        "date_matched": date_matched,
        "amount_matched": amount_matched,
        "description_matched": description_matched,
        "reference_matched": reference_matched,
        "date_difference_days": date_diff,
        "amount_difference": float(amount_diff),
        "description_similarity": description_similarity
    }
    
    return final_score, criteria

def get_matched_fields(criteria: Dict[str, Any]) -> List[str]:
    """Get list of fields that matched"""
    matched_fields = []
    
    if criteria.get("date_matched"):
        matched_fields.append("date")
    
    if criteria.get("amount_matched"):
        matched_fields.append("amount")
    
    if criteria.get("description_matched"):
        matched_fields.append("description")
    
    if criteria.get("reference_matched"):
        matched_fields.append("reference")
    
    return matched_fields