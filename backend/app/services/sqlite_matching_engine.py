"""
Simplified matching engine using direct SQLite queries
"""
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
from app.core.database import execute_query, execute_insert, execute_update
import json

class SimplifiedMatchingEngine:
    def __init__(self, date_tolerance_days: int = 3, amount_tolerance_percent: float = 0.01):
        self.date_tolerance_days = date_tolerance_days
        self.amount_tolerance_percent = amount_tolerance_percent
    
    def find_potential_matches(self, efatura_id: int) -> List[Dict[str, Any]]:
        """Find potential bank movements for an e-fatura record"""
        
        # Get the e-fatura record
        efatura = execute_query(
            "SELECT * FROM efatura_records WHERE id = ?", 
            (efatura_id,)
        )[0]
        
        # Calculate date range
        date_min = (datetime.strptime(efatura['document_date'], '%Y-%m-%d') - 
                   timedelta(days=self.date_tolerance_days)).strftime('%Y-%m-%d')
        date_max = (datetime.strptime(efatura['document_date'], '%Y-%m-%d') + 
                   timedelta(days=self.date_tolerance_days)).strftime('%Y-%m-%d')
        
        # Calculate amount range
        amount_min = efatura['total_amount'] * (1 - self.amount_tolerance_percent)
        amount_max = efatura['total_amount'] * (1 + self.amount_tolerance_percent)
        
        # Find potential matches
        query = """
        SELECT bm.*, 
               ABS(julianday(bm.movement_date) - julianday(?)) as date_diff,
               ABS(bm.amount - ?) / ? as amount_diff
        FROM bank_movements bm
        WHERE bm.movement_date BETWEEN ? AND ?
          AND bm.amount BETWEEN ? AND ?
          AND bm.status = 'unmatched'
        ORDER BY date_diff ASC, amount_diff ASC
        LIMIT 10
        """
        
        params = (
            efatura['document_date'],
            efatura['total_amount'],
            efatura['total_amount'],
            date_min,
            date_max,
            amount_min,
            amount_max
        )
        
        return execute_query(query, params)
    
    def calculate_match_score(self, efatura: Dict[str, Any], bank_movement: Dict[str, Any]) -> float:
        """Calculate confidence score for a match"""
        score = 0.0
        
        # Date proximity (40% weight)
        date_diff = abs((datetime.strptime(efatura['document_date'], '%Y-%m-%d') - 
                        datetime.strptime(bank_movement['movement_date'], '%Y-%m-%d')).days)
        date_score = max(0, 1 - (date_diff / self.date_tolerance_days)) * 0.4
        score += date_score
        
        # Amount proximity (40% weight)
        amount_diff = abs(efatura['total_amount'] - bank_movement['amount'])
        amount_ratio = amount_diff / efatura['total_amount'] if efatura['total_amount'] > 0 else 1
        amount_score = max(0, 1 - (amount_ratio / self.amount_tolerance_percent)) * 0.4
        score += amount_score
        
        # Reference match (20% weight)
        if efatura.get('reference') and bank_movement.get('reference'):
            if efatura['reference'] in bank_movement['reference'] or \
               bank_movement['reference'] in efatura['reference']:
                score += 0.2
        
        return round(score, 3)
    
    def create_match(self, efatura_id: int, bank_movement_id: int, confidence_score: float) -> int:
        """Create a match between e-fatura and bank movement"""
        
        # Insert match record
        match_id = execute_insert(
            """
            INSERT INTO matches (efatura_id, bank_movement_id, confidence_score, match_type, match_details)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                efatura_id,
                bank_movement_id,
                confidence_score,
                'automatic' if confidence_score >= 0.8 else 'suggested',
                json.dumps({
                    'matched_at': datetime.now().isoformat(),
                    'confidence_score': confidence_score
                })
            )
        )
        
        # Update statuses
        execute_update(
            "UPDATE efatura_records SET status = 'matched' WHERE id = ?",
            (efatura_id,)
        )
        
        execute_update(
            "UPDATE bank_movements SET status = 'matched' WHERE id = ?",
            (bank_movement_id,)
        )
        
        return match_id
    
    def auto_match_all(self) -> Dict[str, Any]:
        """Automatically match all unmatched records"""
        
        # Get all unmatched e-fatura records
        unmatched_efaturas = execute_query(
            "SELECT * FROM efatura_records WHERE status = 'unmatched'"
        )
        
        results = {
            'total_processed': len(unmatched_efaturas),
            'matched': 0,
            'suggested': 0,
            'unmatched': 0
        }
        
        for efatura in unmatched_efaturas:
            potential_matches = self.find_potential_matches(efatura['id'])
            
            if potential_matches:
                best_match = potential_matches[0]
                score = self.calculate_match_score(efatura, best_match)
                
                if score >= 0.8:  # High confidence - auto match
                    self.create_match(efatura['id'], best_match['id'], score)
                    results['matched'] += 1
                elif score >= 0.5:  # Medium confidence - suggest
                    self.create_match(efatura['id'], best_match['id'], score)
                    results['suggested'] += 1
                else:
                    results['unmatched'] += 1
            else:
                results['unmatched'] += 1
        
        return results
    
    def get_match_summary(self) -> Dict[str, Any]:
        """Get summary of matching status"""
        
        summary = execute_query("""
            SELECT 
                (SELECT COUNT(*) FROM efatura_records) as total_efaturas,
                (SELECT COUNT(*) FROM efatura_records WHERE status = 'matched') as matched_efaturas,
                (SELECT COUNT(*) FROM bank_movements) as total_bank_movements,
                (SELECT COUNT(*) FROM bank_movements WHERE status = 'matched') as matched_bank_movements,
                (SELECT COUNT(*) FROM matches) as total_matches,
                (SELECT COUNT(*) FROM matches WHERE confidence_score >= 0.8) as high_confidence_matches
        """)[0]
        
        return summary