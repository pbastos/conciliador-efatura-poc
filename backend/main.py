from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import pandas as pd
import io
from datetime import datetime
import re
from thefuzz import fuzz
import csv
import xlsxwriter
import random

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

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint to verify API is running"""
    return {"status": "healthy", "service": "E-fatura Conciliador API"}

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
                    (document_number, document_type, document_date, supplier_name, supplier_nif, total_amount, tax_amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(row.get('document_number', '')).strip(),
                    str(row.get('document_type', 'Fatura')).strip(),
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
        
        # Run auto-matching after successful upload
        if records_processed > 0:
            match_result = run_auto_match()
        else:
            match_result = {"matches_found": 0}
        
        result = {
            "success": True,
            "filename": file.filename,
            "file_type": file_type,
            "records_processed": records_processed,
            "records_skipped": records_skipped,
            "total_rows": len(df),
            "auto_match": match_result
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
    
    # Get column mappings from settings
    settings = query("SELECT key, value FROM settings WHERE key LIKE 'bank_column_%'")
    column_settings = {item['key']: item['value'] for item in settings}
    
    date_column = column_settings.get('bank_column_date', '')
    description_column = column_settings.get('bank_column_description', '')
    amount_column = column_settings.get('bank_column_amount', '')
    
    # Check if columns are configured
    if not date_column or not description_column or not amount_column:
        raise HTTPException(
            400, 
            "Bank column mappings not configured. Please go to Settings and configure the column names for Date, Description, and Amount before uploading bank files."
        )
    
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
        
        # Use custom column mappings
        column_mapping = {
            date_column: 'movement_date',
            description_column: 'description',
            amount_column: 'amount'
        }
        
        # Also add lowercase versions
        column_mapping[date_column.lower()] = 'movement_date'
        column_mapping[description_column.lower()] = 'description'
        column_mapping[amount_column.lower()] = 'amount'
        
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
                f"Column '{amount_column}' not found in file. Available columns: {available_cols}. Please update column mappings in Settings."
            )
        
        if 'movement_date' not in df.columns:
            available_cols = list(df.columns)
            raise HTTPException(
                400, 
                f"Column '{date_column}' not found in file. Available columns: {available_cols}. Please update column mappings in Settings."
            )
        
        if 'description' not in df.columns:
            available_cols = list(df.columns)
            raise HTTPException(
                400, 
                f"Column '{description_column}' not found in file. Available columns: {available_cols}. Please update column mappings in Settings."
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
        
        # Run auto-matching after successful upload
        if records_processed > 0:
            match_result = run_auto_match()
        else:
            match_result = {"matches_found": 0}
        
        result = {
            "success": True,
            "filename": file.filename,
            "file_type": file_type,
            "records_processed": records_processed,
            "records_skipped": records_skipped,
            "total_rows": len(df),
            "auto_match": match_result
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
    # Get total count for pagination
    total_count = query("""
        SELECT COUNT(*) as count FROM efatura_records
    """)[0]['count']
    
    records = query("""
        SELECT 
            e.id as efatura_id,
            e.document_number,
            e.document_type,
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
    
    return {
        "records": records,
        "total": total_count,
        "limit": limit,
        "offset": offset
    }

# Helper function for auto-matching - exact MyConcierge logic
def calculate_match_confidence_efatura(efatura: Dict[str, Any], bank: Dict[str, Any]) -> float:
    """
    Calculate match confidence for E-fatura to Bank matching.
    Based on MyConcierge's calculate_match_confidence logic with date tolerance.
    """
    confidence = 1.0  # Start with perfect confidence
    
    # Add date proximity factor (within 30 days)
    try:
        efatura_date = datetime.strptime(efatura['document_date'], '%Y-%m-%d').date()
        bank_date = datetime.strptime(bank['movement_date'], '%Y-%m-%d').date()
        days_diff = abs((efatura_date - bank_date).days)
        
        if days_diff == 0:
            # Same day - no reduction
            pass
        elif days_diff <= 7:
            # Within a week - small reduction
            confidence *= 0.95
        elif days_diff <= 30:
            # Within 30 days - gradual reduction
            confidence *= (0.8 + 0.15 * (1 - (days_diff - 7) / 23))
    except:
        confidence *= 0.7  # Significant reduction if dates can't be parsed
    
    # Check description/name matching using fuzzy string matching
    name_match = False
    if bank.get('description') and efatura.get('supplier_name'):
        # Clean and normalize descriptions
        bank_desc = bank['description'].lower().strip()
        supplier_name = efatura['supplier_name'].lower().strip()
        
        # Remove common bank prefixes
        prefixes = ['dd ', 'trf ', 'transf ', 'trans ', 'compra ', 'pagamento ']
        for prefix in prefixes:
            if bank_desc.startswith(prefix):
                bank_desc = bank_desc[len(prefix):]
        
        # Use fuzzy string matching with partial_ratio (like MyConcierge)
        name_score = fuzz.partial_ratio(supplier_name, bank_desc) / 100.0
        name_match = name_score > 0.8
    
    if not name_match:
        confidence *= 0.9  # Reduce confidence by 10% if names don't match well
    
    return confidence

def calculate_match_confidence_bank(bank: Dict[str, Any], efatura: Dict[str, Any]) -> float:
    """
    Calculate match confidence for Bank to E-fatura matching.
    Based on MyConcierge's bank movement matching logic with more tolerant dates.
    """
    confidence = 1.0  # Start with perfect confidence
    
    # Check date proximity (within ±30 days)
    try:
        bank_date = datetime.strptime(bank['movement_date'], '%Y-%m-%d').date()
        efatura_date = datetime.strptime(efatura['document_date'], '%Y-%m-%d').date()
        days_diff = abs((bank_date - efatura_date).days)
        
        if days_diff > 30:
            return 0.0  # Dates too far apart, reject match
        elif days_diff > 5:
            # Gradual reduction for dates beyond 5 days
            confidence *= (0.7 + 0.3 * (1 - (days_diff - 5) / 25))
        elif days_diff > 0:
            # Original MyConcierge logic for first 5 days - reduce by 6% per day
            confidence *= (1 - (days_diff * 0.06))
    except:
        return 0.0
    
    # Check description similarity
    if efatura.get('supplier_name') and bank.get('description'):
        # Clean and normalize descriptions
        bank_desc = bank['description'].lower()
        supplier_name = efatura['supplier_name'].lower()
        
        # Remove common prefixes from bank description
        prefixes = ['dd ', 'trf ', 'transf ', 'trans ']
        for prefix in prefixes:
            if bank_desc.startswith(prefix):
                bank_desc = bank_desc[len(prefix):]
        
        # Calculate similarity score using fuzzy matching
        desc_score = fuzz.partial_ratio(bank_desc, supplier_name) / 100.0
        
        # Description similarity affects up to 50% of the confidence
        confidence *= (0.5 + (desc_score * 0.5))
    
    return confidence

def run_auto_match():
    """
    Run the auto-matching algorithm using MyConcierge logic with date tolerance.
    Match criteria:
    1. For E-fatura matching: Within 30 days, exact amount (0.01 tolerance)
    2. For Bank matching: Within 30 days, exact amount (0.01 tolerance), min 70% confidence
    """
    # Get confidence threshold from settings
    threshold_setting = query("SELECT value FROM settings WHERE key = 'confidence_threshold'")
    confidence_threshold = float(threshold_setting[0]['value']) / 100 if threshold_setting else 0.7
    
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
    skipped_multiple_matches = 0
    skipped_no_matches = 0
    
    # Keep track of matched records to ensure 1:1 matching
    matched_banks = set()
    
    # Match E-fatura records with Bank movements (MyConcierge efatura logic)
    for efatura in efatura_records:
        try:
            efatura_date = datetime.strptime(efatura['document_date'], '%Y-%m-%d').date()
            efatura_total = float(efatura['total_amount'])
            
            # Find all potential matches
            potential_matches = []
            for bank in bank_movements:
                # Skip if already matched
                if bank['id'] in matched_banks:
                    continue
                    
                try:
                    bank_date = datetime.strptime(bank['movement_date'], '%Y-%m-%d').date()
                    bank_total = abs(float(bank['amount']))  # Convert to positive
                    
                    # Check for amount match first (must be exact)
                    if abs(efatura_total - bank_total) < 0.01:
                        # Check date proximity (within 30 days for E-fatura to Bank)
                        days_diff = abs((efatura_date - bank_date).days)
                        if days_diff <= 30:
                            potential_matches.append(bank)
                except:
                    continue
            
            # Skip if multiple matches found (like MyConcierge)
            if len(potential_matches) > 1:
                skipped_multiple_matches += 1
                continue
            
            # Skip if no matches found
            if len(potential_matches) == 0:
                skipped_no_matches += 1
                continue
                
            # Process single match
            bank = potential_matches[0]
            
            # Calculate match confidence using MyConcierge logic
            confidence = calculate_match_confidence_efatura(efatura, bank)
            
            # Create match if confidence is high enough
            if confidence >= confidence_threshold:
                execute("""
                    INSERT INTO matches (efatura_id, bank_id, confidence_score, status)
                    VALUES (?, ?, ?, 'proposed')
                """, (efatura['id'], bank['id'], confidence))
                
                # Update status
                execute("UPDATE efatura_records SET status = 'matched' WHERE id = ?", (efatura['id'],))
                execute("UPDATE bank_movements SET status = 'matched' WHERE id = ?", (bank['id'],))
                
                # Mark bank as matched
                matched_banks.add(bank['id'])
                
                matches_found += 1
                
        except Exception as e:
            continue
    
    # Now try Bank to E-fatura matching for remaining unmatched (MyConcierge bank logic)
    remaining_efatura = query("""
        SELECT * FROM efatura_records 
        WHERE status = 'unmatched'
    """)
    
    remaining_banks = query("""
        SELECT * FROM bank_movements 
        WHERE status = 'unmatched'
    """)
    
    for bank in remaining_banks:
        try:
            bank_date = datetime.strptime(bank['movement_date'], '%Y-%m-%d').date()
            bank_value = abs(float(bank['amount']))
            
            # Find all potential matches within date window
            potential_matches = []
            for efatura in remaining_efatura:
                if efatura.get('status') != 'unmatched':
                    continue
                    
                try:
                    efatura_date = datetime.strptime(efatura['document_date'], '%Y-%m-%d').date()
                    efatura_value = float(efatura['total_amount'])
                    
                    # Check for value match with small tolerance
                    if abs(bank_value - efatura_value) > 0.01:
                        continue
                        
                    # Check date proximity (within 30 days for Bank to E-fatura)
                    if abs((bank_date - efatura_date).days) > 30:
                        continue
                    
                    # Calculate match confidence
                    confidence = calculate_match_confidence_bank(bank, efatura)
                    if confidence >= 0.70:  # MyConcierge uses 70% minimum
                        potential_matches.append((efatura, confidence))
                except:
                    continue
            
            # Skip if multiple matches found
            if len(potential_matches) > 1:
                skipped_multiple_matches += 1
                continue
            
            # Skip if no matches found
            if len(potential_matches) == 0:
                skipped_no_matches += 1
                continue
                
            # Process single match
            efatura, confidence = potential_matches[0]
            
            execute("""
                INSERT INTO matches (efatura_id, bank_id, confidence_score, status)
                VALUES (?, ?, ?, 'proposed')
            """, (efatura['id'], bank['id'], confidence))
            
            # Update status
            execute("UPDATE efatura_records SET status = 'matched' WHERE id = ?", (efatura['id'],))
            execute("UPDATE bank_movements SET status = 'matched' WHERE id = ?", (bank['id'],))
            
            matches_found += 1
            
        except Exception as e:
            continue
    
    return {
        "matches_found": matches_found,
        "efatura_unmatched": len(efatura_records) - matches_found,
        "bank_unmatched": len(bank_movements) - matches_found,
        "skipped_multiple_matches": skipped_multiple_matches,
        "skipped_no_matches": skipped_no_matches
    }

# Simple matching algorithm API endpoint
@app.post("/api/v1/matching/auto-match")
async def auto_match():
    result = run_auto_match()
    return {
        "success": True,
        **result
    }

# Update match status
@app.put("/api/v1/matches/{match_id}/status")
async def update_match_status(match_id: int, status: Dict[str, str]):
    valid_statuses = ['proposed', 'confirmed', 'rejected']
    new_status = status.get('status')
    
    if new_status not in valid_statuses:
        raise HTTPException(400, f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
    
    try:
        # Update match status
        execute("""
            UPDATE matches 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_status, match_id))
        
        # If rejected, update both records to unmatched
        if new_status == 'rejected':
            # Get the match details
            match = query("SELECT efatura_id, bank_id FROM matches WHERE id = ?", (match_id,))
            if match:
                execute("UPDATE efatura_records SET status = 'unmatched' WHERE id = ?", (match[0]['efatura_id'],))
                execute("UPDATE bank_movements SET status = 'unmatched' WHERE id = ?", (match[0]['bank_id'],))
        
        return {"success": True, "status": new_status}
        
    except Exception as e:
        raise HTTPException(500, f"Error updating match status: {str(e)}")

# Create manual match
@app.post("/api/v1/matches")
async def create_manual_match(match_data: Dict[str, Any]):
    efatura_id = match_data.get('efatura_id')
    bank_id = match_data.get('bank_id')
    
    if not efatura_id or not bank_id:
        raise HTTPException(400, "Both efatura_id and bank_id are required")
    
    try:
        # Check if records exist and are unmatched
        efatura = query("SELECT * FROM efatura_records WHERE id = ? AND status = 'unmatched'", (efatura_id,))
        bank = query("SELECT * FROM bank_movements WHERE id = ? AND status = 'unmatched'", (bank_id,))
        
        if not efatura:
            raise HTTPException(404, "E-fatura record not found or already matched")
        if not bank:
            raise HTTPException(404, "Bank movement not found or already matched")
        
        # Create match
        execute("""
            INSERT INTO matches (efatura_id, bank_id, confidence_score, status)
            VALUES (?, ?, 1.0, 'confirmed')
        """, (efatura_id, bank_id))
        
        # Update statuses
        execute("UPDATE efatura_records SET status = 'matched' WHERE id = ?", (efatura_id,))
        execute("UPDATE bank_movements SET status = 'matched' WHERE id = ?", (bank_id,))
        
        return {"success": True, "message": "Manual match created"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error creating manual match: {str(e)}")

# Delete match
@app.delete("/api/v1/matches/{match_id}")
async def delete_match(match_id: int):
    try:
        # Get match details before deletion
        match = query("SELECT efatura_id, bank_id FROM matches WHERE id = ?", (match_id,))
        if not match:
            raise HTTPException(404, "Match not found")
        
        # Delete the match
        execute("DELETE FROM matches WHERE id = ?", (match_id,))
        
        # Update statuses back to unmatched
        execute("UPDATE efatura_records SET status = 'unmatched' WHERE id = ?", (match[0]['efatura_id'],))
        execute("UPDATE bank_movements SET status = 'unmatched' WHERE id = ?", (match[0]['bank_id'],))
        
        return {"success": True, "message": "Match deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error deleting match: {str(e)}")

# Delete all data
@app.delete("/api/v1/data/all")
async def delete_all_data():
    """
    Delete all data from all tables (except the schema).
    This is a dangerous operation and should be used with caution.
    """
    try:
        # Delete in correct order to respect foreign key constraints
        execute("DELETE FROM matches")
        execute("DELETE FROM efatura_records")
        execute("DELETE FROM bank_movements")
        
        # Reset auto-increment counters (SQLite specific)
        execute("DELETE FROM sqlite_sequence WHERE name IN ('matches', 'efatura_records', 'bank_movements')")
        
        return {
            "success": True,
            "message": "Todos os dados foram apagados com sucesso"
        }
        
    except Exception as e:
        raise HTTPException(500, f"Erro ao apagar dados: {str(e)}")

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "SQLite"}

# Helper function to get test companies with realistic bank name variations
def get_test_companies():
    """Returns a list of test companies with realistic bank name variations"""
    return [
        {"nif": "500649839", "name": "Lavandaria a Malita Soeiro e Neves Lda", "sector": "Outros", 
         "bank_names": ["Lavandaria A Malita", "LAVANDARIA MALITA", "Lavandaria a M"]},
        {"nif": "513700641", "name": "Mafalda Sofia Santana Unipessoal Lda", "sector": "Outros",
         "bank_names": ["Sophiprojects Lda", "MAFALDA SANTANA", "M Sofia Santana"]},
        {"nif": "506433269", "name": "Inside Tours, Lda", "sector": "",
         "bank_names": ["Inside Tours", "INSIDE TOURS LDA", "Inside T"]},
        {"nif": "514090634", "name": "ITVault Lda", "sector": "Outros",
         "bank_names": ["ITVault", "ITVAULT LDA", "ITVault Lda"]},
        {"nif": "503630330", "name": "Worten - Equipamentos Para o Lar S A", "sector": "",
         "bank_names": ["WORTEN", "Worten Equipamentos", "WORTEN SA"]},
        {"nif": "505416654", "name": "Ikea Portugal Móveis e Decoração Lda", "sector": "",
         "bank_names": ["IKEA PORTUGAL", "Ikea", "IKEA MOVEIS"]},
        {"nif": "502544180", "name": "Vodafone Portugal - Comunicações Pessoais S A", "sector": "Outros",
         "bank_names": ["VODAFONE", "Vodafone Portugal", "VODAFONE PT"]},
        {"nif": "508346835", "name": "Espazo Plus - Self Solutions Lda", "sector": "",
         "bank_names": ["ESPAZO PLUS SE", "ESPAZO PLUS -", "Espazo Plus"]},
        {"nif": "515225142", "name": "Arcade Choice, Lda", "sector": "Outros",
         "bank_names": ["Arcade Choice", "ARCADE CHOICE", "Arcade Ch"]},
        {"nif": "503619086", "name": "Lousani Cosmética, Lda", "sector": "Outros",
         "bank_names": ["Lousani", "LOUSANI COSMETICA", "Lousani Cosm"]},
        {"nif": "514610247", "name": "Serviços Chave Unipessoal Lda", "sector": "Outros",
         "bank_names": ["Servicos Chave", "SERVICOS CHAVE", "Serv Chave"]},
        {"nif": "503629995", "name": "AutoParts Portugal - Peças Auto Sa", "sector": "",
         "bank_names": ["AUTOPARTS", "AutoParts Portugal", "AutoParts PT"]},
        {"nif": "503311332", "name": "Lisboa Parking - Estacionamento E.M.", "sector": "Outros",
         "bank_names": ["LISBOA PARKING", "Lisboa Park", "LX Parking"]},
        {"nif": "514948809", "name": "C Santos SA", "sector": "",
         "bank_names": ["C SANTOS SA", "C Santos", "CSANTOS"]},
        {"nif": "510938507", "name": "FFH Self Storage", "sector": "Outros",
         "bank_names": ["FFH Self Stora", "FFH SELF STORAGE", "FFH Storage"]},
        {"nif": "517318555", "name": "Divicode Lda", "sector": "",
         "bank_names": ["DIVICODE LDA", "Divicode", "DIVICODE"]},
        {"nif": "503226696", "name": "Mobile World SA", "sector": "",
         "bank_names": ["MOBILE WORLD SA", "Mobile World", "MOBILE W"]},
        {"nif": "518173097", "name": "Chaves Areeiro", "sector": "Outros",
         "bank_names": ["CHAVES AREEIRO", "Chaves Areeiro 1", "Ch Areeiro"]},
        {"nif": "514458984", "name": "AccoPrime Consultores", "sector": "",
         "bank_names": ["Accoprime", "ACCOPRIME", "AccoPrime"]},
        {"nif": "500521662", "name": "Auto Repair Centro Lda", "sector": "Manutenção e reparação de veículos automóveis",
         "bank_names": ["Auto Repair", "AUTO REPAIR CENTRO", "Auto Rep"]},
        {"nif": "509584489", "name": "Fleet Management Lda", "sector": "Outros",
         "bank_names": ["Fleet Management", "FLEET MGMT", "Fleet Mgmt"]},
        {"nif": "502011475", "name": "Supermercado Central S A", "sector": "",
         "bank_names": ["SUPERMERCADO CENTRAL", "Super Central", "Sup Central"]},
        {"nif": "516701258", "name": "Diagnostics Lab Lda", "sector": "Outros",
         "bank_names": ["Diagnostics Lab", "DIAGNOSTICS", "Diag Lab"]},
        {"nif": "515696935", "name": "Office Solutions Lda", "sector": "",
         "bank_names": ["Office Solutions", "OFFICE SOL", "Office Sol"]},
        {"nif": "503020532", "name": "Adega Premium, S.A.", "sector": "",
         "bank_names": ["Adega Premium", "ADEGA PREMIUM", "Adega Prem"]},
        {"nif": "501234567", "name": "TechSolutions Portugal Lda", "sector": "Tecnologia",
         "bank_names": ["TechSolutions", "TECHSOLUTIONS", "Tech Sol"]},
        {"nif": "507890123", "name": "Green Energy Services SA", "sector": "Energia",
         "bank_names": ["Green Energy", "GREEN ENERGY SVC", "Green En"]},
        {"nif": "509876543", "name": "Porto Digital Marketing Lda", "sector": "Marketing",
         "bank_names": ["Porto Digital", "PORTO DIGITAL MKT", "Porto Dig"]},
        {"nif": "512345678", "name": "Café Central Lisboa Lda", "sector": "Restauração",
         "bank_names": ["Cafe Central", "CAFE CENTRAL LX", "Cafe C"]},
        {"nif": "505123456", "name": "AutoService Norte SA", "sector": "Automóvel",
         "bank_names": ["AutoService", "AUTOSERVICE NORTE", "Auto Serv"]},
        {"nif": "508765432", "name": "CleanMax - Serviços de Limpeza Lda", "sector": "Serviços",
         "bank_names": ["CleanMax", "CLEANMAX SERVICOS", "Clean Max"]},
        {"nif": "514567890", "name": "DataCenter Solutions Lda", "sector": "Tecnologia",
         "bank_names": ["DataCenter Sol", "DATACENTER", "Data Center"]},
        {"nif": "511234567", "name": "Fitness Club Porto SA", "sector": "Desporto",
         "bank_names": ["Fitness Club", "FITNESS CLUB PRT", "Fit Club"]},
        {"nif": "516789012", "name": "Smart Home Technologies Lda", "sector": "Tecnologia",
         "bank_names": ["Smart Home", "SMART HOME TECH", "Smart H"]},
        {"nif": "513456789", "name": "Bio Market Portugal SA", "sector": "Retalho",
         "bank_names": ["Bio Market", "BIO MARKET PT", "Bio Mkt"]},
        {"nif": "517890123", "name": "Digital Print Express Lda", "sector": "Impressão",
         "bank_names": ["Digital Print", "DIGITAL PRINT EXP", "Dig Print"]},
        {"nif": "510123456", "name": "Security Systems Pro SA", "sector": "Segurança",
         "bank_names": ["Security Sys", "SECURITY SYSTEMS", "Sec Systems"]},
        {"nif": "515678901", "name": "Cloud Services Portugal Lda", "sector": "Tecnologia",
         "bank_names": ["Cloud Services", "CLOUD SERVICES PT", "Cloud Serv"]},
        {"nif": "512890123", "name": "Fast Delivery Express SA", "sector": "Logística",
         "bank_names": ["Fast Delivery", "FAST DELIVERY", "Fast Del"]},
        {"nif": "518345678", "name": "Medical Center Lisboa Lda", "sector": "Saúde",
         "bank_names": ["Medical Center", "MEDICAL CENTER LX", "Med Center"]},
        {"nif": "509012345", "name": "Pet Care Services Lda", "sector": "Animais",
         "bank_names": ["Pet Care", "PET CARE SERVICES", "Pet C"]},
        {"nif": "514789012", "name": "Construction Pro SA", "sector": "Construção",
         "bank_names": ["Construction Pro", "CONSTRUCTION PRO", "Const Pro"]},
        {"nif": "511567890", "name": "Travel Agency Porto Lda", "sector": "Turismo",
         "bank_names": ["Travel Agency", "TRAVEL AGENCY PRT", "Travel A"]},
        {"nif": "516234567", "name": "Solar Panel Installers SA", "sector": "Energia",
         "bank_names": ["Solar Panel", "SOLAR PANEL INST", "Solar P"]},
        {"nif": "513890123", "name": "Bakery Fresh Daily Lda", "sector": "Alimentação",
         "bank_names": ["Bakery Fresh", "BAKERY FRESH", "Bakery F"]}
    ]

# Generate dummy E-fatura file
@app.get("/api/v1/test-data/generate-efatura")
async def generate_dummy_efatura():
    """Generate a dummy E-fatura CSV file with 300 records based on realistic data"""
    from fastapi.responses import Response
    import random
    from datetime import datetime, timedelta
    
    # Get test companies with realistic bank name variations
    companies = get_test_companies()
    
    # Shared amounts that will match with bank movements
    shared_amounts = [
        3563.03, 3489.89, 3321.00, 3173.03, 2829.00, 2460.00, 1670.40, 1406.39,
        974.79, 777.00, 486.00, 461.77, 461.25, 438.90, 434.37, 394.52,
        388.00, 369.00, 340.82, 329.96, 289.05, 270.95, 250.00, 221.84,
        221.40, 188.00, 184.50, 178.35, 170.96, 147.60, 124.04, 115.62,
        114.50, 111.98, 110.93, 108.56, 98.21, 320.00, 88.22, 80.98,
        79.90, 78.35, 72.85, 69.96, 66.94, 65.00, 61.50, 59.79,
        58.00, 55.95, 54.30, 52.12, 49.98, 48.50, 46.75, 45.00,
        43.20, 41.90, 39.99, 38.50, 37.00, 35.95, 34.50, 33.00,
        31.50, 30.00, 28.90, 27.50, 26.00, 24.99, 23.50, 22.00,
        21.00, 19.99, 18.50, 17.00, 16.50, 15.99, 14.50, 13.00,
        12.50, 11.99, 10.50, 9.99, 8.50, 7.99, 6.50, 5.99
    ]
    
    # Add more random amounts to reach 200 shared amounts
    while len(shared_amounts) < 200:
        shared_amounts.append(round(random.uniform(10, 1000), 2))
    
    # Generate dates for the last 4 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=120)
    
    # CSV header with BOM for Excel compatibility
    csv_lines = ['Setor;Emitente;Nº Fatura / ATCUD;Tipo;Data Emissão;Total;IVA;Base Tributável;Situação;Comunicação  Emitente;Comunicação  Adquirente']
    
    # Generate 300 records
    for i in range(300):
        # Random date
        random_days = random.randint(0, 120)
        doc_date = start_date + timedelta(days=random_days)
        
        # Use shared amounts for first 200, random for the rest
        if i < 200:
            total = shared_amounts[i]
            # For matching records, use the same company pattern as bank movements
            company_index = i % len(companies)
            company = companies[company_index]
        else:
            total = round(random.uniform(10, 1000), 2)
            # For non-matching records, use random companies
            company = random.choice(companies)
        
        # Calculate VAT (various rates used in Portugal)
        vat_rates = [0.23, 0.13, 0.06]  # Normal, Intermediate, Reduced
        vat_rate = random.choice(vat_rates) if random.random() > 0.8 else 0.23  # 80% use normal rate
        base = round(total / (1 + vat_rate), 2)
        vat = round(total - base, 2)
        
        # Generate realistic invoice number
        doc_types = ["FT", "FR", "FAC", "FS", "F"]
        doc_type = random.choice(doc_types)
        invoice_num = f"{doc_type} {doc_date.strftime('%Y')}/{i+1:04d} / JF{random.randint(100000, 999999)}-{i+1}"
        
        # Document type
        tipos = ["Fatura", "Fatura-recibo", "Fatura simplificada", "Nota de crédito"]
        tipo = random.choice(tipos) if random.random() > 0.1 else "Fatura"
        
        # Create CSV line with proper formatting
        total_str = f"{total:.2f} €".replace('.', ',')
        vat_str = f"{vat:.2f} €".replace('.', ',')
        base_str = f"{base:.2f} €".replace('.', ',')
        
        line = f'"{company["sector"]}";"{company["nif"]} - {company["name"]}";"{invoice_num}";"{tipo}";"{doc_date.strftime("%Y-%m-%d")}";"{total_str}";"{vat_str}";"{base_str}";"Registado";"X";""'
        csv_lines.append(line)
    
    # Join all lines
    csv_content = "\n".join(csv_lines)
    
    # Return as CSV file with UTF-8 BOM
    return Response(
        content=csv_content.encode('utf-8-sig'),
        media_type='text/csv; charset=utf-8',
        headers={
            'Content-Disposition': 'attachment; filename="efatura_test_300_records.csv"'
        }
    )

# Generate dummy bank movements file
@app.get("/api/v1/test-data/generate-bank")
async def generate_dummy_bank():
    """Generate a dummy bank movements Excel file with 250 records based on realistic data"""
    from fastapi.responses import Response
    import random
    from datetime import datetime, timedelta
    import xlsxwriter
    import io
    
    # Get column names from settings
    settings = query("SELECT key, value FROM settings WHERE key LIKE 'bank_column_%'")
    column_settings = {item['key']: item['value'] for item in settings}
    
    date_column = column_settings.get('bank_column_date', '')
    description_column = column_settings.get('bank_column_description', '')
    amount_column = column_settings.get('bank_column_amount', '')
    
    # If columns not configured, use defaults from real bank file
    if not date_column:
        date_column = 'Data Lançamento'
    if not description_column:
        description_column = 'Descrição'
    if not amount_column:
        amount_column = 'Montante'
    
    # Use the same companies as E-fatura to ensure consistent matching
    companies = get_test_companies()
    
    # Additional names for non-matching movements (like personal transfers)
    person_names = [
        "João Silva", "Maria Santos", "Pedro Costa", "Ana Ferreira",
        "Carlos Oliveira", "Sofia Rodrigues", "Miguel Pereira", "Beatriz Alves",
        "Ricardo Martins", "Catarina Sousa", "Tiago Fernandes", "Inês Gonçalves",
        "André Lopes", "Mariana Ribeiro", "Bruno Cardoso", "Rita Nunes"
    ]
    
    # Shared amounts that will match with E-fatura
    shared_amounts = [
        3563.03, 3489.89, 3321.00, 3173.03, 2829.00, 2460.00, 1670.40, 1406.39,
        974.79, 777.00, 486.00, 461.77, 461.25, 438.90, 434.37, 394.52,
        388.00, 369.00, 340.82, 329.96, 289.05, 270.95, 250.00, 221.84,
        221.40, 188.00, 184.50, 178.35, 170.96, 147.60, 124.04, 115.62,
        114.50, 111.98, 110.93, 108.56, 98.21, 320.00, 88.22, 80.98,
        79.90, 78.35, 72.85, 69.96, 66.94, 65.00, 61.50, 59.79,
        58.00, 55.95, 54.30, 52.12, 49.98, 48.50, 46.75, 45.00,
        43.20, 41.90, 39.99, 38.50, 37.00, 35.95, 34.50, 33.00,
        31.50, 30.00, 28.90, 27.50, 26.00, 24.99, 23.50, 22.00,
        21.00, 19.99, 18.50, 17.00, 16.50, 15.99, 14.50, 13.00,
        12.50, 11.99, 10.50, 9.99, 8.50, 7.99, 6.50, 5.99
    ]
    
    # Add more random amounts to reach 200 shared amounts
    while len(shared_amounts) < 200:
        shared_amounts.append(round(random.uniform(10, 1000), 2))
    
    # Generate dates for the last 4 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=120)
    
    # Create in-memory Excel file
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet()
    
    # Add bank header rows (mimicking real bank export format)
    worksheet.write(0, 0, 'Millennium bcp')
    worksheet.write(1, 0, 'Conta')
    worksheet.write(1, 2, '0000012345678901 - EUR')
    worksheet.write(2, 0, 'Data de inicio')
    worksheet.write(2, 2, start_date.strftime('%d/%m/%Y'))
    worksheet.write(3, 0, 'Data fim')
    worksheet.write(3, 2, end_date.strftime('%d/%m/%Y'))
    worksheet.write(4, 0, 'Tipos de Pesquisa')
    worksheet.write(4, 2, 'Todos')
    worksheet.write(5, 0, 'Data de exportação')
    worksheet.write(5, 2, datetime.now().strftime('%d-%m-%Y %H:%M:%S'))
    
    # Empty row
    worksheet.write(6, 0, '')
    
    # Add column headers
    headers = [date_column, 'Data Valor', description_column, amount_column, 'Saldo Contabilistico', 'Moeda', 'Notas', 'Tratado']
    for col, header in enumerate(headers):
        worksheet.write(7, col, header)
    
    # Generate 250 records
    balance = 50000.00  # Starting balance
    movements = []
    
    # Keep track of which companies we've used for each amount
    amount_to_company = {}
    
    # First, create 200 matching movements
    for i in range(200):
        random_days = random.randint(0, 120)
        date_offset = random.randint(0, 3)  # Bank movements usually happen a few days after invoice
        movement_date = start_date + timedelta(days=random_days + date_offset)
        
        amount = -shared_amounts[i]  # Negative for payments
        
        # For consistent matching, use the same company index as in E-fatura
        company_index = i % len(companies)
        company = companies[company_index]
        
        # Store which company we used for this amount (for matching)
        amount_to_company[shared_amounts[i]] = company
        
        # Use bank_names for realistic bank descriptions
        bank_name = random.choice(company['bank_names'])
        
        # Create realistic payment descriptions using bank_names
        desc_variations = [
            f"TRF P/ {bank_name}",
            f"DD {bank_name}",
            f"TRANSF {bank_name}",
            f"TRF {bank_name}",
            f"PAGAMENTO {bank_name}",
            f"{bank_name}",
            f"ORDEM PERMANENTE {bank_name}",
            f"{bank_name} LISBOA PRT",
            f"TRF. P/O {bank_name} FT",
            f"DD {bank_name}"
        ]
        
        # Choose a random variation
        description = random.choice(desc_variations)
        
        movements.append({
            'date': movement_date,
            'description': description,
            'amount': amount,
            'is_match': True
        })
    
    # Add 50 non-matching movements (personal transfers, ATM, etc.)
    for i in range(50):
        random_days = random.randint(0, 120)
        movement_date = start_date + timedelta(days=random_days)
        
        # Random amounts for non-matching movements
        amount = round(random.uniform(-500, 500), 2)
        
        # Various types of non-matching movements
        movement_types = [
            lambda: f"TRF P/ {random.choice(person_names)}",
            lambda: f"LEV ATM {random.randint(1000, 9999)}",
            lambda: "COMISSAO MANUTENCAO CONTA",
            lambda: f"DD PayPal {random.randint(1000000, 9999999)}",
            lambda: "TRF RECEBIDA",
            lambda: f"MB WAY P/ {random.choice(person_names)}",
            lambda: "IMPOSTO SELO",
            lambda: "JURO CREDITO HABITACAO"
        ]
        
        description = random.choice(movement_types)()
        
        movements.append({
            'date': movement_date,
            'description': description,
            'amount': amount,
            'is_match': False
        })
    
    # Sort movements by date (descending, like real bank statements)
    movements.sort(key=lambda x: x['date'], reverse=True)
    
    # Write movements to Excel
    for i, movement in enumerate(movements):
        row = i + 8  # Starting after headers
        
        # Update balance
        balance += movement['amount']
        
        # Write row data
        worksheet.write(row, 0, movement['date'].strftime('%d/%m/%Y'))
        worksheet.write(row, 1, movement['date'].strftime('%d/%m/%Y'))  # Data Valor same as Data Lançamento
        worksheet.write(row, 2, movement['description'])
        worksheet.write(row, 3, movement['amount'])
        worksheet.write(row, 4, balance)
        worksheet.write(row, 5, 'EUR')
        worksheet.write(row, 6, None)  # Notas
        worksheet.write(row, 7, 'Não')  # Tratado
    
    workbook.close()
    output.seek(0)
    
    # Return as Excel file
    return Response(
        content=output.read(),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={
            'Content-Disposition': 'attachment; filename="bank_movements_test_250_records.xlsx"'
        }
    )

# Get settings
@app.get("/api/v1/settings")
async def get_settings():
    """Get all settings"""
    try:
        settings = query("SELECT key, value FROM settings")
        # Convert to dict for easier access
        settings_dict = {item['key']: item['value'] for item in settings}
        return settings_dict
    except Exception as e:
        raise HTTPException(500, f"Error retrieving settings: {str(e)}")

# Update a setting
@app.put("/api/v1/settings/{key}")
async def update_setting(key: str, setting: Dict[str, Any]):
    """Update a specific setting"""
    value = setting.get('value')
    if value is None:
        raise HTTPException(400, "Value is required")
    
    try:
        # Check if setting exists
        existing = query("SELECT id FROM settings WHERE key = ?", (key,))
        
        if existing:
            # Update existing setting
            execute("""
                UPDATE settings 
                SET value = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE key = ?
            """, (str(value), key))
        else:
            # Insert new setting
            execute("""
                INSERT INTO settings (key, value) 
                VALUES (?, ?)
            """, (key, str(value)))
        
        return {"success": True, "key": key, "value": value}
    except Exception as e:
        raise HTTPException(500, f"Error updating setting: {str(e)}")

# Get bank movements with matches
@app.get("/api/v1/bank/records-with-matches")
async def get_bank_reconciliation(limit: int = 100, offset: int = 0):
    # Get total count for pagination
    total_count = query("""
        SELECT COUNT(*) as count FROM bank_movements
    """)[0]['count']
    
    records = query("""
        SELECT 
            b.id as bank_id,
            b.movement_date,
            b.description as bank_description,
            b.amount as bank_amount,
            b.reference as bank_reference,
            b.status as bank_status,
            m.id as match_id,
            m.confidence_score,
            m.status as match_status,
            e.id as efatura_id,
            e.document_number,
            e.document_type,
            e.document_date,
            e.supplier_name,
            e.supplier_nif,
            e.total_amount,
            e.tax_amount
        FROM 
            bank_movements b
        LEFT JOIN 
            matches m ON b.id = m.bank_id AND m.status != 'rejected'
        LEFT JOIN 
            efatura_records e ON m.efatura_id = e.id
        ORDER BY 
            b.movement_date DESC, b.created_at DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))
    
    return {
        "records": records,
        "total": total_count,
        "limit": limit,
        "offset": offset
    }

# Get matching summary stats
@app.get("/api/v1/matching/summary")
async def get_matching_summary():
    """Get summary statistics for matching"""
    try:
        total_efatura = query("SELECT COUNT(*) as count FROM efatura_records")[0]['count']
        total_bank = query("SELECT COUNT(*) as count FROM bank_movements")[0]['count']
        total_matches = query("SELECT COUNT(*) as count FROM matches WHERE status != 'rejected'")[0]['count']
        unmatched_efatura = query("SELECT COUNT(*) as count FROM efatura_records WHERE status = 'unmatched'")[0]['count']
        unmatched_bank = query("SELECT COUNT(*) as count FROM bank_movements WHERE status = 'unmatched'")[0]['count']
        
        match_rate = 0
        if total_efatura > 0:
            match_rate = (total_matches / total_efatura) * 100
        
        return {
            "total_efatura_records": total_efatura,
            "total_bank_records": total_bank,
            "total_matches": total_matches,
            "unmatched_efatura_records": unmatched_efatura,
            "unmatched_bank_records": unmatched_bank,
            "match_rate": match_rate
        }
    except Exception as e:
        raise HTTPException(500, f"Error getting matching summary: {str(e)}")