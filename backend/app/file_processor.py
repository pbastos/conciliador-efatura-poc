import pandas as pd
import io
from datetime import datetime
from app.database import get_db_cursor, insert_efatura_records, insert_bank_movements

def clean_currency(value):
    """Clean currency values"""
    if pd.isna(value) or value == '':
        return 0.0
    
    if isinstance(value, (int, float)):
        return float(value)
    
    # Remove currency symbols and convert
    value_str = str(value).replace('€', '').replace(' ', '')
    
    # Handle European format (comma as decimal)
    if ',' in value_str and '.' in value_str:
        value_str = value_str.replace('.', '').replace(',', '.')
    elif ',' in value_str:
        value_str = value_str.replace(',', '.')
    
    try:
        return float(value_str)
    except:
        return 0.0

def process_efatura_file(file_contents, filename, batch_id):
    """Process e-fatura Excel/CSV file"""
    try:
        # Read file
        if filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(file_contents), sep=';', encoding='utf-8-sig')
        else:
            df = pd.read_excel(io.BytesIO(file_contents))
        
        # Column mapping
        column_mapping = {
            "Setor": "sector",
            "Emitente": "issuer",
            "Nº Fatura / ATCUD": "invoice",
            "Tipo": "document_type",
            "Data Emissão": "issue_date",
            "Total": "total",
            "IVA": "tax_amount",
            "Base Tributável": "tax_base",
            "Situação": "status"
        }
        
        # Process records
        records = []
        for _, row in df.iterrows():
            try:
                # Parse date
                date_str = row.get("Data Emissão", "")
                if pd.notna(date_str):
                    if isinstance(date_str, str) and '/' in date_str:
                        date_obj = datetime.strptime(date_str, '%d/%m/%Y')
                    else:
                        date_obj = pd.to_datetime(date_str)
                    issue_date = date_obj.strftime('%Y-%m-%d')
                else:
                    continue
                
                record = {
                    'issuer': str(row.get("Emitente", "")).strip(),
                    'invoice': str(row.get("Nº Fatura / ATCUD", "")).strip(),
                    'document_type': str(row.get("Tipo", "")).strip(),
                    'issue_date': issue_date,
                    'total': clean_currency(row.get("Total", 0)),
                    'tax_amount': clean_currency(row.get("IVA", 0)),
                    'tax_base': clean_currency(row.get("Base Tributável", 0)),
                    'status': str(row.get("Situação", "")).strip()
                }
                records.append(record)
            except Exception as e:
                print(f"Error processing row: {e}")
                continue
        
        # Insert records
        if records:
            count = insert_efatura_records(records, batch_id)
            return {"success": True, "records_processed": count, "total_rows": len(df)}
        else:
            return {"success": False, "error": "No valid records found"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

def process_bank_file(file_contents, filename, batch_id):
    """Process bank movements Excel/CSV file"""
    try:
        # Read file
        if filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(file_contents), encoding='utf-8-sig')
        else:
            df = pd.read_excel(io.BytesIO(file_contents))
        
        # Try to identify columns
        possible_date_cols = ["Data Movimento", "Data", "Date", "Movement Date"]
        possible_desc_cols = ["Descrição", "Descricao", "Description"]
        possible_amount_cols = ["Montante", "Valor", "Amount", "Value"]
        
        date_col = next((col for col in possible_date_cols if col in df.columns), None)
        desc_col = next((col for col in possible_desc_cols if col in df.columns), None)
        amount_col = next((col for col in possible_amount_cols if col in df.columns), None)
        
        if not all([date_col, desc_col, amount_col]):
            return {"success": False, "error": "Required columns not found"}
        
        # Process records
        records = []
        for _, row in df.iterrows():
            try:
                # Parse date
                date_obj = pd.to_datetime(row[date_col])
                movement_date = date_obj.strftime('%Y-%m-%d')
                
                record = {
                    'movement_date': movement_date,
                    'value_date': movement_date,  # Default to same date
                    'description': str(row[desc_col]).strip(),
                    'amount': clean_currency(row[amount_col]),
                    'balance': clean_currency(row.get("Saldo", 0)) if "Saldo" in row else None,
                    'reference': str(row.get("Referência", "")).strip() if "Referência" in row else None
                }
                records.append(record)
            except Exception as e:
                print(f"Error processing row: {e}")
                continue
        
        # Insert records
        if records:
            count = insert_bank_movements(records, batch_id)
            return {"success": True, "records_processed": count, "total_rows": len(df)}
        else:
            return {"success": False, "error": "No valid records found"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}