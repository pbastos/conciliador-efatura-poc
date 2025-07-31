import pandas as pd
import io
from typing import Dict, List, Any
from datetime import datetime
import traceback

from app.core.database import supabase
from app.utils.excel_parser import parse_efatura_excel, parse_bank_excel

async def process_efatura_file(
    file_contents: bytes,
    filename: str,
    upload_id: str,
    org_id: str
) -> Dict[str, Any]:
    """Process uploaded e-fatura file"""
    try:
        # Parse the Excel file
        records = parse_efatura_excel(file_contents, filename)
        
        if not records:
            return {
                "success": False,
                "records_processed": 0,
                "records_failed": 0,
                "error": "No valid records found in file"
            }
        
        # Process records in batches
        batch_size = 100
        total_processed = 0
        total_failed = 0
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            
            # Add metadata to each record
            for record in batch:
                record["org_id"] = org_id
                record["file_upload_id"] = upload_id
                record["created_at"] = datetime.utcnow().isoformat()
                record["updated_at"] = datetime.utcnow().isoformat()
            
            try:
                # Insert batch into database
                result = supabase.table("efatura_records").insert(batch).execute()
                total_processed += len(result.data)
            except Exception as e:
                print(f"Error inserting batch: {str(e)}")
                total_failed += len(batch)
        
        return {
            "success": True,
            "records_processed": total_processed,
            "records_failed": total_failed,
            "message": f"Processed {total_processed} records successfully"
        }
        
    except Exception as e:
        print(f"Error processing e-fatura file: {str(e)}")
        traceback.print_exc()
        return {
            "success": False,
            "records_processed": 0,
            "records_failed": 0,
            "error": str(e)
        }

async def process_bank_file(
    file_contents: bytes,
    filename: str,
    upload_id: str,
    org_id: str
) -> Dict[str, Any]:
    """Process uploaded bank movements file"""
    try:
        # Parse the Excel file
        records = parse_bank_excel(file_contents, filename)
        
        if not records:
            return {
                "success": False,
                "records_processed": 0,
                "records_failed": 0,
                "error": "No valid records found in file"
            }
        
        # Process records in batches
        batch_size = 100
        total_processed = 0
        total_failed = 0
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            
            # Add metadata to each record
            for record in batch:
                record["org_id"] = org_id
                record["file_upload_id"] = upload_id
                record["created_at"] = datetime.utcnow().isoformat()
                record["updated_at"] = datetime.utcnow().isoformat()
            
            try:
                # Insert batch into database
                result = supabase.table("bank_movements").insert(batch).execute()
                total_processed += len(result.data)
            except Exception as e:
                print(f"Error inserting batch: {str(e)}")
                total_failed += len(batch)
        
        return {
            "success": True,
            "records_processed": total_processed,
            "records_failed": total_failed,
            "message": f"Processed {total_processed} records successfully"
        }
        
    except Exception as e:
        print(f"Error processing bank file: {str(e)}")
        traceback.print_exc()
        return {
            "success": False,
            "records_processed": 0,
            "records_failed": 0,
            "error": str(e)
        }