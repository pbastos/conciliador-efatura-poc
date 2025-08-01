from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import pandas as pd
import io
from datetime import datetime
import re

from database import init_db, query, execute

def parse_currency(value):
    """Parse European currency format to float"""
    if pd.isna(value) or value == '':
        return 0.0
    
    if isinstance(value, (int, float)):
        return float(value)
    
    # Convert to string and clean
    value_str = str(value)
    
    # Remove currency symbols and spaces
    value_str = value_str.replace('€', '').replace('EUR', '').replace(' ', '')
    
    # Handle European format (1.234,56) vs US format (1,234.56)
    if ',' in value_str and '.' in value_str:
        # If both exist, assume . is thousand separator and , is decimal
        value_str = value_str.replace('.', '').replace(',', '.')
    elif ',' in value_str:
        # Just comma, likely decimal separator
        value_str = value_str.replace(',', '.')
    
    try:
        return float(value_str)
    except:
        return 0.0

def parse_date(date_value, formats=None):
    """Parse date with multiple format support"""
    if pd.isna(date_value) or date_value == '':
        return None
    
    if formats is None:
        formats = [
            '%d/%m/%Y',      # DD/MM/YYYY
            '%d-%m-%Y',      # DD-MM-YYYY
            '%Y-%m-%d',      # YYYY-MM-DD
            '%d.%m.%Y',      # DD.MM.YYYY
            '%Y/%m/%d',      # YYYY/MM/DD
            '%d/%m/%y',      # DD/MM/YY
            '%d-%m-%y',      # DD-MM-YY
        ]
    
    date_str = str(date_value).strip()
    
    for date_format in formats:
        try:
            return datetime.strptime(date_str, date_format).strftime('%Y-%m-%d')
        except:
            continue
    
    # Try pandas parser as fallback
    try:
        return pd.to_datetime(date_value).strftime('%Y-%m-%d')
    except:
        return None

def find_header_row(df, expected_headers):
    """Find the row containing headers in a dataframe"""
    for idx in range(min(20, len(df))):  # Check first 20 rows
        row_values = df.iloc[idx].astype(str).str.lower().tolist()
        # Check if any expected header is in this row
        matches = sum(1 for header in expected_headers if any(header.lower() in cell for cell in row_values))
        if matches >= 2:  # At least 2 headers match
            return idx
    return None

# Initialize FastAPI app
app = FastAPI(title="E-fatura Reconciliation API", version="1.0.0")

# Configure CORS - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "E-fatura Reconciliation API is running"}

# Upload e-fatura file
@app.post("/api/v1/efatura/upload")
async def upload_efatura(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(400, "Invalid file format. Please upload Excel or CSV file.")
    
    contents = await file.read()
    
    try:
        df = None
        file_type = None
        
        # Try reading as CSV first (common for e-fatura exports)
        if file.filename.endswith('.csv'):
            try:
                # Try semicolon delimiter (Portuguese standard)
                df = pd.read_csv(io.BytesIO(contents), sep=';', encoding='utf-8-sig')
                file_type = 'csv'
            except:
                try:
                    # Try comma delimiter
                    df = pd.read_csv(io.BytesIO(contents), sep=',', encoding='utf-8-sig')
                    file_type = 'csv'
                except Exception as e:
                    print(f"CSV parsing failed: {e}")
        
        # Try Excel if CSV fails or for Excel files
        if df is None:
            try:
                # First, read without header to detect structure
                raw_df = pd.read_excel(io.BytesIO(contents), header=None, engine='openpyxl')
                
                # Expected headers for e-fatura
                expected_headers = ['setor', 'emitente', 'fatura', 'tipo', 'data', 'total', 'iva', 'base']
                
                # Find header row
                header_row = find_header_row(raw_df, expected_headers)
                
                if header_row is not None:
                    # Read with detected header row
                    df = pd.read_excel(io.BytesIO(contents), header=header_row, engine='openpyxl')
                else:
                    # Try default first row as header
                    df = pd.read_excel(io.BytesIO(contents), engine='openpyxl')
                
                file_type = 'excel'
            except:
                try:
                    # Try xlrd engine for older Excel files
                    df = pd.read_excel(io.BytesIO(contents), engine='xlrd')
                    file_type = 'excel'
                except Exception as e:
                    raise HTTPException(400, f"Could not read file. Please ensure it's a valid Excel or CSV file. Error: {str(e)}")
        
        if df is None or df.empty:
            raise HTTPException(400, "File is empty or could not be parsed")
        
        # Extended column mapping based on MyConcierge implementation
        column_mapping = {
            # E-fatura standard columns
            'Setor': 'sector',
            'Emitente': 'supplier_name',
            'Nº Fatura / ATCUD': 'document_number',
            'Tipo': 'document_type',
            'Data Emissão': 'document_date',
            'Total': 'total_amount',
            'IVA': 'tax_amount',
            'Base Tributável': 'taxable_base',
            'Situação': 'status',
            # Alternative column names
            'Número do Documento': 'document_number',
            'Data do Documento': 'document_date',
            'Nome do Fornecedor': 'supplier_name',
            'NIF do Fornecedor': 'supplier_nif',
            'NIF': 'supplier_nif',
            'Valor Total': 'total_amount',
            'Valor IVA': 'tax_amount',
            # Lowercase versions
            'setor': 'sector',
            'emitente': 'supplier_name',
            'nº fatura / atcud': 'document_number',
            'tipo': 'document_type',
            'data emissão': 'document_date',
            'total': 'total_amount',
            'iva': 'tax_amount',
            'base tributável': 'taxable_base',
            'situação': 'status'
        }
        
        # Normalize column names (remove extra spaces, lowercase)
        df.columns = df.columns.str.strip()
        
        # Create a mapping for current columns
        rename_dict = {}
        for col in df.columns:
            normalized_col = col.strip()
            if normalized_col in column_mapping:
                rename_dict[col] = column_mapping[normalized_col]
            elif normalized_col.lower() in column_mapping:
                rename_dict[col] = column_mapping[normalized_col.lower()]
        
        # Rename columns
        if rename_dict:
            df = df.rename(columns=rename_dict)
        
        # Validate required columns
        required_columns = ['total_amount']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            available_cols = list(df.columns)
            raise HTTPException(
                400, 
                f"Missing required columns: {missing_columns}. Available columns: {available_cols}"
            )
        
        # Process each row
        records_processed = 0
        records_skipped = 0
        errors = []
        
        for idx, row in df.iterrows():
            try:
                # Skip empty rows
                if pd.isna(row.get('total_amount')) or row.get('total_amount') == '':
                    records_skipped += 1
                    continue
                
                # Parse amounts
                total_amount = parse_currency(row.get('total_amount', 0))
                tax_amount = parse_currency(row.get('tax_amount', 0))
                
                # Skip if total is 0
                if total_amount == 0:
                    records_skipped += 1
                    continue
                
                # Parse date
                doc_date = parse_date(row.get('document_date'))
                
                # Get supplier NIF - extract numbers only
                supplier_nif = str(row.get('supplier_nif', ''))
                if supplier_nif:
                    # Extract only numbers from NIF
                    supplier_nif = re.sub(r'[^0-9]', '', supplier_nif)
                
                # Insert record
                execute("""
                    INSERT INTO efatura_records 
                    (document_number, document_date, supplier_name, supplier_nif, total_amount, tax_amount)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    str(row.get('document_number', '')).strip(),
                    doc_date,
                    str(row.get('supplier_name', '')).strip(),
                    supplier_nif,
                    total_amount,
                    tax_amount
                ))
                records_processed += 1
                
            except Exception as row_error:
                errors.append(f"Row {idx + 1}: {str(row_error)}")
                records_skipped += 1
        
        result = {
            "success": True,
            "filename": file.filename,
            "file_type": file_type,
            "records_processed": records_processed,
            "records_skipped": records_skipped,
            "total_rows": len(df)
        }
        
        if errors:
            result["warnings"] = errors[:10]  # Show first 10 errors
            if len(errors) > 10:
                result["warnings"].append(f"... and {len(errors) - 10} more errors")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error processing file: {str(e)}")

# Upload bank file
@app.post("/api/v1/bank/upload")
async def upload_bank(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(400, "Invalid file format. Please upload Excel or CSV file.")
    
    contents = await file.read()
    
    try:
        df = None
        file_type = None
        
        # Try reading as CSV first
        if file.filename.endswith('.csv'):
            try:
                # Try semicolon delimiter (Portuguese standard)
                df = pd.read_csv(io.BytesIO(contents), sep=';', encoding='utf-8-sig')
                file_type = 'csv'
            except:
                try:
                    # Try comma delimiter
                    df = pd.read_csv(io.BytesIO(contents), sep=',', encoding='utf-8-sig')
                    file_type = 'csv'
                except Exception as e:
                    print(f"CSV parsing failed: {e}")
        
        # Try Excel if CSV fails or for Excel files
        if df is None:
            try:
                # First, read without header to detect structure
                raw_df = pd.read_excel(io.BytesIO(contents), header=None, engine='openpyxl')
                
                # Expected headers for bank statements
                expected_headers = ['data', 'movimento', 'descrição', 'valor', 'montante', 'débito', 'crédito']
                
                # Find header row
                header_row = find_header_row(raw_df, expected_headers)
                
                if header_row is not None:
                    # Read with detected header row
                    df = pd.read_excel(io.BytesIO(contents), header=header_row, engine='openpyxl')
                else:
                    # Try default first row as header
                    df = pd.read_excel(io.BytesIO(contents), engine='openpyxl')
                
                file_type = 'excel'
            except:
                try:
                    # Try xlrd engine for older Excel files
                    df = pd.read_excel(io.BytesIO(contents), engine='xlrd')
                    file_type = 'excel'
                except Exception as e:
                    raise HTTPException(400, f"Could not read file. Please ensure it's a valid Excel or CSV file. Error: {str(e)}")
        
        if df is None or df.empty:
            raise HTTPException(400, "File is empty or could not be parsed")
        
        # Extended column mapping for bank files
        column_mapping = {
            # Common Portuguese bank columns
            'Data Movimento': 'movement_date',
            'Data Lançamento': 'movement_date',
            'Data Valor': 'movement_date',
            'Data': 'movement_date',
            'Descrição': 'description',
            'Descricao': 'description',
            'Descrição do Movimento': 'description',
            'Histórico': 'description',
            'Montante': 'amount',
            'Valor': 'amount',
            'Débito': 'debit',
            'Crédito': 'credit',
            'Referência': 'reference',
            'Ref': 'reference',
            'Ref.': 'reference',
            'Saldo': 'balance',
            # Lowercase versions
            'data movimento': 'movement_date',
            'data lançamento': 'movement_date',
            'data valor': 'movement_date',
            'data': 'movement_date',
            'descrição': 'description',
            'descricao': 'description',
            'descrição do movimento': 'description',
            'histórico': 'description',
            'montante': 'amount',
            'valor': 'amount',
            'débito': 'debit',
            'crédito': 'credit',
            'referência': 'reference',
            'ref': 'reference',
            'ref.': 'reference',
            'saldo': 'balance'
        }
        
        # Normalize column names
        df.columns = df.columns.str.strip()
        
        # Create a mapping for current columns
        rename_dict = {}
        for col in df.columns:
            normalized_col = col.strip()
            if normalized_col in column_mapping:
                rename_dict[col] = column_mapping[normalized_col]
            elif normalized_col.lower() in column_mapping:
                rename_dict[col] = column_mapping[normalized_col.lower()]
        
        # Rename columns
        if rename_dict:
            df = df.rename(columns=rename_dict)
        
        # Handle debit/credit columns if present
        if 'debit' in df.columns and 'credit' in df.columns and 'amount' not in df.columns:
            # Combine debit and credit into amount (negative for debit)
            df['amount'] = df.apply(
                lambda row: -parse_currency(row.get('debit', 0)) if pd.notna(row.get('debit')) and parse_currency(row.get('debit', 0)) != 0
                else parse_currency(row.get('credit', 0)), 
                axis=1
            )
        
        # Validate required columns
        if 'amount' not in df.columns:
            available_cols = list(df.columns)
            raise HTTPException(
                400, 
                f"Missing required column 'amount' (or 'debit'/'credit'). Available columns: {available_cols}"
            )
        
        # Process each row
        records_processed = 0
        records_skipped = 0
        errors = []
        
        for idx, row in df.iterrows():
            try:
                # Get amount
                amount = parse_currency(row.get('amount', 0))
                
                # Skip rows without amount
                if amount == 0 and pd.isna(row.get('amount')):
                    records_skipped += 1
                    continue
                
                # Parse date
                mov_date = parse_date(row.get('movement_date'))
                
                # Get description
                description = str(row.get('description', '')).strip()
                
                # Skip if no description and no amount
                if not description and amount == 0:
                    records_skipped += 1
                    continue
                
                # Insert record
                execute("""
                    INSERT INTO bank_movements 
                    (movement_date, description, amount, reference)
                    VALUES (?, ?, ?, ?)
                """, (
                    mov_date,
                    description,
                    amount,
                    str(row.get('reference', '')).strip()
                ))
                records_processed += 1
                
            except Exception as row_error:
                errors.append(f"Row {idx + 1}: {str(row_error)}")
                records_skipped += 1
        
        result = {
            "success": True,
            "filename": file.filename,
            "file_type": file_type,
            "records_processed": records_processed,
            "records_skipped": records_skipped,
            "total_rows": len(df)
        }
        
        if errors:
            result["warnings"] = errors[:10]  # Show first 10 errors
            if len(errors) > 10:
                result["warnings"].append(f"... and {len(errors) - 10} more errors")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error processing file: {str(e)}")

# Get e-fatura records
@app.get("/api/v1/efatura/records")
async def get_efatura_records(limit: int = 100, offset: int = 0):
    records = query("""
        SELECT * FROM efatura_records 
        ORDER BY document_date DESC 
        LIMIT ? OFFSET ?
    """, (limit, offset))
    return records

# Get bank records
@app.get("/api/v1/bank/records")
async def get_bank_records(limit: int = 100, offset: int = 0):
    records = query("""
        SELECT * FROM bank_movements 
        ORDER BY movement_date DESC 
        LIMIT ? OFFSET ?
    """, (limit, offset))
    return records

# Get reconciliation view (e-fatura records with matches)
@app.get("/api/v1/efatura/records-with-matches")
async def get_reconciliation(limit: int = 100, offset: int = 0):
    records = query("""
        SELECT 
            e.id as efatura_id,
            e.document_number,
            e.document_date,
            e.supplier_name,
            e.supplier_nif,
            e.total_amount,
            e.tax_amount,
            e.status as efatura_status,
            m.id as match_id,
            m.confidence_score,
            m.status as match_status,
            b.id as bank_id,
            b.movement_date,
            b.description as bank_description,
            b.amount as bank_amount,
            b.reference as bank_reference
        FROM 
            efatura_records e
        LEFT JOIN 
            matches m ON e.id = m.efatura_id AND m.status != 'rejected'
        LEFT JOIN 
            bank_movements b ON m.bank_id = b.id
        ORDER BY 
            e.document_date DESC, e.created_at DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))
    return records

# Simple matching algorithm
@app.post("/api/v1/matching/auto-match")
async def auto_match():
    # Get unmatched records
    efatura_records = query("""
        SELECT * FROM efatura_records 
        WHERE status = 'unmatched'
    """)
    
    bank_movements = query("""
        SELECT * FROM bank_movements 
        WHERE status = 'unmatched'
    """)
    
    matches_found = 0
    
    # Simple matching by amount and date proximity
    for efatura in efatura_records:
        best_match = None
        best_score = 0
        
        for bank in bank_movements:
            # Skip if already matched
            if bank.get('status') != 'unmatched':
                continue
                
            # Calculate match score
            score = 0
            
            # Exact amount match
            if abs(efatura['total_amount'] - abs(bank['amount'])) < 0.01:
                score += 0.7
            # Close amount (within 1%)
            elif abs(efatura['total_amount'] - abs(bank['amount'])) / efatura['total_amount'] < 0.01:
                score += 0.5
            else:
                continue  # Skip if amount doesn't match
            
            # Date proximity (same month)
            if efatura['document_date'] and bank['movement_date']:
                try:
                    e_date = datetime.strptime(efatura['document_date'], '%Y-%m-%d')
                    b_date = datetime.strptime(bank['movement_date'], '%Y-%m-%d')
                    
                    days_diff = abs((e_date - b_date).days)
                    if days_diff <= 30:
                        score += 0.3 * (1 - days_diff / 30)
                except:
                    pass
            
            if score > best_score:
                best_score = score
                best_match = bank
        
        # Create match if score is high enough
        if best_match and best_score >= 0.7:
            execute("""
                INSERT INTO matches (efatura_id, bank_id, confidence_score)
                VALUES (?, ?, ?)
            """, (efatura['id'], best_match['id'], best_score))
            
            # Update status
            execute("UPDATE efatura_records SET status = 'matched' WHERE id = ?", (efatura['id'],))
            execute("UPDATE bank_movements SET status = 'matched' WHERE id = ?", (best_match['id'],))
            
            matches_found += 1
    
    return {
        "success": True,
        "matches_found": matches_found,
        "efatura_unmatched": len(efatura_records) - matches_found,
        "bank_unmatched": len(bank_movements) - matches_found
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "SQLite"}