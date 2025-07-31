import pandas as pd
import io
from typing import List, Dict, Any
from datetime import datetime

def parse_efatura_excel(file_contents: bytes, filename: str) -> List[Dict[str, Any]]:
    """Parse e-fatura Excel file and return list of records"""
    try:
        # Try to read Excel file
        if filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(file_contents), sep=';', encoding='utf-8-sig')
        else:
            df = pd.read_excel(io.BytesIO(file_contents))
        
        # Expected column mapping for e-fatura
        column_mapping = {
            "Setor": "sector",
            "Emitente": "supplier_name",
            "Nº Fatura / ATCUD": "document_number",
            "Tipo": "document_type",
            "Data Emissão": "document_date",
            "Total": "total_amount",
            "IVA": "tax_amount",
            "Base Tributável": "taxable_base",
            "Situação": "status",
            "NIF": "supplier_nif"
        }
        
        # Rename columns
        df = df.rename(columns=column_mapping)
        
        # Clean and convert data
        records = []
        for _, row in df.iterrows():
            record = {}
            
            # Document number
            if 'document_number' in row and pd.notna(row['document_number']):
                record['document_number'] = str(row['document_number']).strip()
            
            # Document date
            if 'document_date' in row and pd.notna(row['document_date']):
                try:
                    # Try to parse different date formats
                    if isinstance(row['document_date'], str):
                        if '/' in row['document_date']:
                            date_obj = datetime.strptime(row['document_date'], '%d/%m/%Y')
                        else:
                            date_obj = datetime.strptime(row['document_date'], '%Y-%m-%d')
                    else:
                        date_obj = pd.to_datetime(row['document_date'])
                    
                    record['document_date'] = date_obj.strftime('%Y-%m-%d')
                except:
                    continue  # Skip records with invalid dates
            else:
                continue  # Date is required
            
            # Supplier info
            record['supplier_name'] = str(row.get('supplier_name', '')).strip() if pd.notna(row.get('supplier_name')) else None
            record['supplier_nif'] = str(row.get('supplier_nif', '')).strip() if pd.notna(row.get('supplier_nif')) else None
            
            # Amounts
            try:
                record['total_amount'] = clean_currency_value(row.get('total_amount', 0))
                record['tax_amount'] = clean_currency_value(row.get('tax_amount', 0))
                record['taxable_base'] = clean_currency_value(row.get('taxable_base', 0))
            except:
                continue  # Skip records with invalid amounts
            
            # Other fields
            record['document_type'] = str(row.get('document_type', '')).strip() if pd.notna(row.get('document_type')) else None
            record['description'] = str(row.get('description', '')).strip() if pd.notna(row.get('description')) else None
            
            # Store raw data
            record['raw_data'] = row.to_dict()
            
            records.append(record)
        
        return records
        
    except Exception as e:
        print(f"Error parsing e-fatura Excel: {str(e)}")
        raise

def parse_bank_excel(file_contents: bytes, filename: str) -> List[Dict[str, Any]]:
    """Parse bank movements Excel file and return list of records"""
    try:
        # Try to read Excel file
        if filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(file_contents), encoding='utf-8-sig')
        else:
            df = pd.read_excel(io.BytesIO(file_contents))
        
        # Common column mappings for bank files
        column_mapping = {
            "Data Movimento": "movement_date",
            "Data Valor": "value_date",
            "Descrição": "description",
            "Montante": "amount",
            "Saldo": "balance",
            "Referência": "reference",
            "Tipo": "movement_type",
            # Alternative names
            "Data": "movement_date",
            "Valor": "amount",
            "Descricao": "description",
            "Ref": "reference"
        }
        
        # Try to identify columns
        df_columns_lower = {col.lower(): col for col in df.columns}
        
        # Rename columns based on mapping
        rename_dict = {}
        for mapped_name, target_name in column_mapping.items():
            if mapped_name in df.columns:
                rename_dict[mapped_name] = target_name
            elif mapped_name.lower() in df_columns_lower:
                rename_dict[df_columns_lower[mapped_name.lower()]] = target_name
        
        df = df.rename(columns=rename_dict)
        
        # Clean and convert data
        records = []
        for _, row in df.iterrows():
            record = {}
            
            # Movement date (required)
            if 'movement_date' in row and pd.notna(row['movement_date']):
                try:
                    date_obj = pd.to_datetime(row['movement_date'])
                    record['movement_date'] = date_obj.strftime('%Y-%m-%d')
                except:
                    continue  # Skip records with invalid dates
            else:
                continue  # Date is required
            
            # Value date (optional)
            if 'value_date' in row and pd.notna(row['value_date']):
                try:
                    date_obj = pd.to_datetime(row['value_date'])
                    record['value_date'] = date_obj.strftime('%Y-%m-%d')
                except:
                    record['value_date'] = record['movement_date']
            else:
                record['value_date'] = record['movement_date']
            
            # Amount (required)
            try:
                record['amount'] = clean_currency_value(row.get('amount', 0))
            except:
                continue  # Skip records with invalid amounts
            
            # Other fields
            record['description'] = str(row.get('description', '')).strip() if pd.notna(row.get('description')) else None
            record['reference'] = str(row.get('reference', '')).strip() if pd.notna(row.get('reference')) else None
            record['balance'] = clean_currency_value(row.get('balance', 0)) if pd.notna(row.get('balance')) else None
            
            # Determine movement type
            if record['amount'] < 0:
                record['movement_type'] = 'Débito'
            else:
                record['movement_type'] = 'Crédito'
            
            # Store raw data
            record['raw_data'] = row.to_dict()
            
            records.append(record)
        
        return records
        
    except Exception as e:
        print(f"Error parsing bank Excel: {str(e)}")
        raise

def clean_currency_value(value) -> float:
    """Clean currency value string and convert to float"""
    if pd.isna(value) or value == '':
        return 0.0
    
    if isinstance(value, (int, float)):
        return float(value)
    
    # Convert to string and clean
    value_str = str(value)
    
    # Remove currency symbols and spaces
    value_str = value_str.replace('€', '').replace('EUR', '').replace(' ', '')
    
    # Handle European number format (comma as decimal separator)
    if ',' in value_str and '.' in value_str:
        # Assume . is thousand separator and , is decimal
        value_str = value_str.replace('.', '').replace(',', '.')
    elif ',' in value_str:
        # Just comma, could be decimal separator
        value_str = value_str.replace(',', '.')
    
    try:
        return float(value_str)
    except:
        return 0.0