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
        # Read Excel file - try different engines
        try:
            df = pd.read_excel(io.BytesIO(contents), engine='openpyxl')
        except:
            try:
                df = pd.read_excel(io.BytesIO(contents), engine='xlrd')
            except:
                # Try as CSV if Excel fails
                df = pd.read_csv(io.BytesIO(contents), sep=';', encoding='utf-8-sig')
        
        # Expected columns (Portuguese)
        column_mapping = {
            'Número do Documento': 'document_number',
            'Nº Fatura / ATCUD': 'document_number',
            'Data do Documento': 'document_date',
            'Data Emissão': 'document_date',
            'Nome do Fornecedor': 'supplier_name',
            'Emitente': 'supplier_name',
            'NIF do Fornecedor': 'supplier_nif',
            'NIF': 'supplier_nif',
            'Total': 'total_amount',
            'IVA': 'tax_amount'
        }
        
        # Rename columns if they match
        for pt_col, en_col in column_mapping.items():
            if pt_col in df.columns:
                df = df.rename(columns={pt_col: en_col})
        
        # Process each row
        records_processed = 0
        for _, row in df.iterrows():
            # Skip rows without essential data
            if pd.isna(row.get('total_amount', 0)):
                continue
                
            # Parse date
            doc_date = None
            if 'document_date' in row and pd.notna(row['document_date']):
                try:
                    doc_date = pd.to_datetime(row['document_date']).strftime('%Y-%m-%d')
                except:
                    pass
            
            # Insert record
            execute("""
                INSERT INTO efatura_records 
                (document_number, document_date, supplier_name, supplier_nif, total_amount, tax_amount)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                str(row.get('document_number', '')),
                doc_date,
                str(row.get('supplier_name', '')),
                str(row.get('supplier_nif', '')),
                parse_currency(row.get('total_amount', 0)),
                parse_currency(row.get('tax_amount', 0))
            ))
            records_processed += 1
        
        return {
            "success": True,
            "filename": file.filename,
            "records_processed": records_processed
        }
        
    except Exception as e:
        raise HTTPException(500, f"Error processing file: {str(e)}")

# Upload bank file
@app.post("/api/v1/bank/upload")
async def upload_bank(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(400, "Invalid file format. Please upload Excel or CSV file.")
    
    contents = await file.read()
    
    try:
        # Read Excel file - try different engines
        try:
            df = pd.read_excel(io.BytesIO(contents), engine='openpyxl')
        except:
            try:
                df = pd.read_excel(io.BytesIO(contents), engine='xlrd')
            except:
                # Try as CSV if Excel fails
                df = pd.read_csv(io.BytesIO(contents), sep=';', encoding='utf-8-sig')
        
        # Expected columns (Portuguese)
        column_mapping = {
            'Data Movimento': 'movement_date',
            'Data': 'movement_date',
            'Descrição': 'description',
            'Descricao': 'description',
            'Montante': 'amount',
            'Valor': 'amount',
            'Referência': 'reference',
            'Ref': 'reference'
        }
        
        # Rename columns if they match
        for pt_col, en_col in column_mapping.items():
            if pt_col in df.columns:
                df = df.rename(columns={pt_col: en_col})
        
        # Process each row
        records_processed = 0
        for _, row in df.iterrows():
            # Skip rows without essential data
            if pd.isna(row.get('amount', 0)):
                continue
                
            # Parse date
            mov_date = None
            if 'movement_date' in row and pd.notna(row['movement_date']):
                try:
                    mov_date = pd.to_datetime(row['movement_date']).strftime('%Y-%m-%d')
                except:
                    pass
            
            # Insert record
            execute("""
                INSERT INTO bank_movements 
                (movement_date, description, amount, reference)
                VALUES (?, ?, ?, ?)
            """, (
                mov_date,
                str(row.get('description', '')),
                parse_currency(row.get('amount', 0)),
                str(row.get('reference', ''))
            ))
            records_processed += 1
        
        return {
            "success": True,
            "filename": file.filename,
            "records_processed": records_processed
        }
        
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