from datetime import datetime
from thefuzz import fuzz
from app.database import get_unmatched_efatura, get_unmatched_bank_movements, create_match

def calculate_match_score(efatura, bank_movement, tolerance_days=5, amount_tolerance=0.01):
    """Calculate matching score between e-fatura and bank movement"""
    score = 0.0
    
    # Amount matching (weight: 40%)
    efatura_amount = abs(float(efatura['total']))
    bank_amount = abs(float(bank_movement['amount']))
    amount_diff = abs(efatura_amount - bank_amount)
    
    if amount_diff < 0.01:  # Exact match
        score += 0.4
    elif amount_diff <= efatura_amount * amount_tolerance:
        score += 0.4 * (1 - amount_diff / (efatura_amount * amount_tolerance))
    else:
        return 0.0  # No match if amount difference too large
    
    # Date matching (weight: 30%)
    efatura_date = datetime.strptime(efatura['issue_date'], '%Y-%m-%d')
    bank_date = datetime.strptime(bank_movement['movement_date'], '%Y-%m-%d')
    days_diff = abs((efatura_date - bank_date).days)
    
    if days_diff == 0:
        score += 0.3
    elif days_diff <= tolerance_days:
        score += 0.3 * (1 - days_diff / tolerance_days)
    
    # Description matching (weight: 30%)
    if efatura['issuer'] and bank_movement['description']:
        # Fuzzy matching on issuer name in description
        similarity = fuzz.partial_ratio(
            efatura['issuer'].lower(),
            bank_movement['description'].lower()
        ) / 100.0
        score += 0.3 * similarity
        
        # Bonus if invoice number appears in description
        if efatura['invoice'] in bank_movement['description']:
            score = min(score + 0.1, 1.0)
    
    return score

def run_automatic_matching(min_confidence=0.5):
    """Run automatic matching process"""
    results = {
        'matches_created': 0,
        'efatura_processed': 0,
        'bank_processed': 0,
        'errors': []
    }
    
    try:
        # Get unmatched records
        efatura_records = get_unmatched_efatura()
        bank_movements = get_unmatched_bank_movements()
        
        results['efatura_processed'] = len(efatura_records)
        results['bank_processed'] = len(bank_movements)
        
        # Track used bank movements
        used_bank_ids = set()
        
        # Process each e-fatura record
        for efatura in efatura_records:
            best_match = None
            best_score = 0
            
            # Find best matching bank movement
            for bank in bank_movements:
                if bank['id'] in used_bank_ids:
                    continue
                    
                score = calculate_match_score(efatura, bank)
                
                if score > best_score and score >= min_confidence:
                    best_match = bank
                    best_score = score
            
            # Create match if found
            if best_match:
                match_id = create_match(
                    efatura['id'],
                    best_match['id'],
                    best_score,
                    'automatic'
                )
                used_bank_ids.add(best_match['id'])
                results['matches_created'] += 1
        
    except Exception as e:
        results['errors'].append(str(e))
    
    return results

def get_match_suggestions(efatura_id=None, bank_movement_id=None, top_n=5):
    """Get matching suggestions for a specific record"""
    suggestions = []
    
    try:
        if efatura_id:
            # Get e-fatura record
            from app.database import get_db_cursor
            with get_db_cursor() as cursor:
                cursor.execute("SELECT * FROM efatura WHERE id = ?", (efatura_id,))
                efatura = dict(cursor.fetchone())
                
                # Get all unmatched bank movements
                bank_movements = get_unmatched_bank_movements()
                
                # Calculate scores
                for bank in bank_movements:
                    score = calculate_match_score(efatura, bank)
                    if score > 0:
                        suggestions.append({
                            'bank_movement': bank,
                            'score': score
                        })
                
                # Sort by score and return top N
                suggestions.sort(key=lambda x: x['score'], reverse=True)
                return suggestions[:top_n]
                
        elif bank_movement_id:
            # Similar logic for bank movement -> e-fatura suggestions
            from app.database import get_db_cursor
            with get_db_cursor() as cursor:
                cursor.execute("SELECT * FROM bank_movements WHERE id = ?", (bank_movement_id,))
                bank = dict(cursor.fetchone())
                
                efatura_records = get_unmatched_efatura()
                
                for efatura in efatura_records:
                    score = calculate_match_score(efatura, bank)
                    if score > 0:
                        suggestions.append({
                            'efatura': efatura,
                            'score': score
                        })
                
                suggestions.sort(key=lambda x: x['score'], reverse=True)
                return suggestions[:top_n]
    
    except Exception as e:
        print(f"Error getting suggestions: {e}")
    
    return suggestions