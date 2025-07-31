"""
Simplified file processor for Excel uploads using direct SQLite
"""
import pandas as pd
from typing import Dict, Any, List
import uuid
from datetime import datetime
from app.core.database import execute_insert, execute_many, execute_query
import os

class SimplifiedFileProcessor:
    
    @staticmethod
    def process_efatura_file(file_path: str, filename: str) -> Dict[str, Any]:
        """Process e-fatura Excel file and store in SQLite"""
        
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Generate upload ID
            upload_id = str(uuid.uuid4())
            
            # Normalize column names (handle Portuguese names)
            column_mapping = {
                'Número do Documento': 'document_number',
                'Data do Documento': 'document_date',
                'Tipo de Documento': 'document_type',
                'NIF do Fornecedor': 'supplier_nif',
                'Nome do Fornecedor': 'supplier_name',
                'NIF do Cliente': 'client_nif',
                'Nome do Cliente': 'client_name',
                'Total': 'total_amount',
                'IVA': 'tax_amount',
                'Base': 'net_amount',
                'Descrição': 'description',
                'Referência': 'reference'
            }
            
            # Rename columns
            df.rename(columns=column_mapping, inplace=True)
            
            # Prepare data for insertion
            records = []
            for _, row in df.iterrows():
                record = (
                    upload_id,
                    row.get('document_number', ''),
                    pd.to_datetime(row.get('document_date')).strftime('%Y-%m-%d') if pd.notna(row.get('document_date')) else None,
                    row.get('document_type', ''),
                    str(row.get('supplier_nif', '')),
                    row.get('supplier_name', ''),
                    str(row.get('client_nif', '')),
                    row.get('client_name', ''),
                    float(row.get('total_amount', 0)),
                    float(row.get('tax_amount', 0)),
                    float(row.get('net_amount', 0)),
                    row.get('description', ''),
                    row.get('reference', ''),
                    'unmatched'
                )
                records.append(record)
            
            # Insert records
            query = """
            INSERT INTO efatura_records 
            (upload_id, document_number, document_date, document_type, supplier_nif, 
             supplier_name, client_nif, client_name, total_amount, tax_amount, 
             net_amount, description, reference, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            rows_inserted = execute_many(query, records)
            
            # Record upload
            execute_insert(
                "INSERT INTO uploads (id, filename, file_type, record_count) VALUES (?, ?, ?, ?)",
                (upload_id, filename, 'efatura', rows_inserted)
            )
            
            return {
                'success': True,
                'upload_id': upload_id,
                'records_processed': rows_inserted,
                'filename': filename
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'filename': filename
            }
        finally:
            # Clean up uploaded file
            if os.path.exists(file_path):
                os.remove(file_path)
    
    @staticmethod
    def process_bank_file(file_path: str, filename: str) -> Dict[str, Any]:
        """Process bank movements Excel file and store in SQLite"""
        
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Generate upload ID
            upload_id = str(uuid.uuid4())
            
            # Normalize column names (handle Portuguese names)
            column_mapping = {
                'Data Movimento': 'movement_date',
                'Data Valor': 'value_date',
                'Descrição': 'description',
                'Montante': 'amount',
                'Saldo': 'balance',
                'Referência': 'reference',
                'Tipo': 'movement_type'
            }
            
            # Rename columns
            df.rename(columns=column_mapping, inplace=True)
            
            # Prepare data for insertion
            records = []
            for _, row in df.iterrows():
                record = (
                    upload_id,
                    pd.to_datetime(row.get('movement_date')).strftime('%Y-%m-%d') if pd.notna(row.get('movement_date')) else None,
                    pd.to_datetime(row.get('value_date')).strftime('%Y-%m-%d') if pd.notna(row.get('value_date')) else None,
                    row.get('description', ''),
                    float(row.get('amount', 0)),
                    float(row.get('balance', 0)),
                    row.get('reference', ''),
                    row.get('movement_type', 'debit' if float(row.get('amount', 0)) < 0 else 'credit'),
                    'unmatched'
                )
                records.append(record)
            
            # Insert records
            query = """
            INSERT INTO bank_movements 
            (upload_id, movement_date, value_date, description, amount, 
             balance, reference, movement_type, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            rows_inserted = execute_many(query, records)
            
            # Record upload
            execute_insert(
                "INSERT INTO uploads (id, filename, file_type, record_count) VALUES (?, ?, ?, ?)",
                (upload_id, filename, 'bank', rows_inserted)
            )
            
            return {
                'success': True,
                'upload_id': upload_id,
                'records_processed': rows_inserted,
                'filename': filename
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'filename': filename
            }
        finally:
            # Clean up uploaded file
            if os.path.exists(file_path):
                os.remove(file_path)
    
    @staticmethod
    def get_upload_history() -> List[Dict[str, Any]]:
        """Get history of all uploads"""
        return execute_query(
            """
            SELECT * FROM uploads 
            ORDER BY upload_date DESC 
            LIMIT 50
            """
        )