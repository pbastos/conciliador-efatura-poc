import pandas as pd
from io import BytesIO
from typing import List, Dict, Any
from datetime import datetime

def generate_matching_report(
    matched_results: List[Dict[str, Any]],
    unmatched_efatura: List[Dict[str, Any]],
    unmatched_bank: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Generate a comprehensive matching report"""
    report = {
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {
            "total_matches": len(matched_results),
            "confirmed_matches": sum(1 for m in matched_results if m["status"] == "confirmed"),
            "proposed_matches": sum(1 for m in matched_results if m["status"] == "proposed"),
            "rejected_matches": sum(1 for m in matched_results if m["status"] == "rejected"),
            "unmatched_efatura": len(unmatched_efatura),
            "unmatched_bank": len(unmatched_bank)
        },
        "confidence_distribution": {
            "high": sum(1 for m in matched_results if m["confidence_score"] >= 0.9),
            "medium": sum(1 for m in matched_results if 0.7 <= m["confidence_score"] < 0.9),
            "low": sum(1 for m in matched_results if m["confidence_score"] < 0.7)
        }
    }
    
    return report

def export_to_excel(
    matched_results: List[Dict[str, Any]],
    unmatched_efatura: List[Dict[str, Any]],
    unmatched_bank: List[Dict[str, Any]]
) -> bytes:
    """Export matching results to Excel file"""
    # Create Excel writer
    buffer = BytesIO()
    
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        # Matched records sheet
        if matched_results:
            matched_df = pd.DataFrame([{
                "E-fatura Document": m["efatura_records"]["document_number"],
                "E-fatura Date": m["efatura_records"]["document_date"],
                "Supplier": m["efatura_records"]["supplier_name"],
                "E-fatura Amount": m["efatura_records"]["total_amount"],
                "Bank Date": m["bank_movements"]["movement_date"],
                "Bank Description": m["bank_movements"]["description"],
                "Bank Amount": m["bank_movements"]["amount"],
                "Confidence Score": f"{m['confidence_score']:.2%}",
                "Status": m["status"],
                "Date Difference": m["date_difference"],
                "Amount Difference": m["amount_difference"]
            } for m in matched_results])
            
            matched_df.to_excel(writer, sheet_name='Matched Records', index=False)
            
            # Format the Excel sheet
            worksheet = writer.sheets['Matched Records']
            for column in matched_df:
                column_width = max(matched_df[column].astype(str).map(len).max(), len(column)) + 2
                col_idx = matched_df.columns.get_loc(column)
                worksheet.column_dimensions[chr(65 + col_idx)].width = column_width
        
        # Unmatched e-fatura sheet
        if unmatched_efatura:
            efatura_df = pd.DataFrame([{
                "Document Number": r["document_number"],
                "Date": r["document_date"],
                "Supplier NIF": r["supplier_nif"],
                "Supplier Name": r["supplier_name"],
                "Total Amount": r["total_amount"],
                "Description": r["description"]
            } for r in unmatched_efatura])
            
            efatura_df.to_excel(writer, sheet_name='Unmatched E-fatura', index=False)
        
        # Unmatched bank movements sheet
        if unmatched_bank:
            bank_df = pd.DataFrame([{
                "Movement Date": r["movement_date"],
                "Value Date": r["value_date"],
                "Description": r["description"],
                "Amount": r["amount"],
                "Reference": r["reference"],
                "Type": r["movement_type"]
            } for r in unmatched_bank])
            
            bank_df.to_excel(writer, sheet_name='Unmatched Bank', index=False)
        
        # Summary sheet
        summary_data = {
            "Metric": [
                "Total Matched Records",
                "Confirmed Matches",
                "Proposed Matches",
                "Rejected Matches",
                "Unmatched E-fatura Records",
                "Unmatched Bank Movements"
            ],
            "Count": [
                len(matched_results),
                sum(1 for m in matched_results if m["status"] == "confirmed"),
                sum(1 for m in matched_results if m["status"] == "proposed"),
                sum(1 for m in matched_results if m["status"] == "rejected"),
                len(unmatched_efatura),
                len(unmatched_bank)
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
    
    buffer.seek(0)
    return buffer.getvalue()