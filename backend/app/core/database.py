import sqlite3
import os
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple
import json
from datetime import datetime

# Database file path
DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'conciliador.db')

def dict_factory(cursor, row):
    """Convert SQLite rows to dictionaries"""
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initialize database with tables"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # E-fatura records table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS efatura_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            upload_id TEXT NOT NULL,
            document_number TEXT,
            document_date DATE,
            document_type TEXT,
            supplier_nif TEXT,
            supplier_name TEXT,
            client_nif TEXT,
            client_name TEXT,
            total_amount REAL,
            tax_amount REAL,
            net_amount REAL,
            description TEXT,
            reference TEXT,
            status TEXT DEFAULT 'unmatched',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Bank movements table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bank_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            upload_id TEXT NOT NULL,
            movement_date DATE,
            value_date DATE,
            description TEXT,
            amount REAL,
            balance REAL,
            reference TEXT,
            movement_type TEXT,
            status TEXT DEFAULT 'unmatched',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Matches table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            efatura_id INTEGER NOT NULL,
            bank_movement_id INTEGER NOT NULL,
            confidence_score REAL,
            match_type TEXT,
            match_details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (efatura_id) REFERENCES efatura_records(id),
            FOREIGN KEY (bank_movement_id) REFERENCES bank_movements(id),
            UNIQUE(efatura_id, bank_movement_id)
        )
        """)
        
        # Uploads table for tracking file uploads
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            record_count INTEGER,
            status TEXT DEFAULT 'completed'
        )
        """)
        
        # Create indexes for better performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_efatura_upload ON efatura_records(upload_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_efatura_date ON efatura_records(document_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_efatura_amount ON efatura_records(total_amount)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bank_upload ON bank_movements(upload_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bank_date ON bank_movements(movement_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bank_amount ON bank_movements(amount)")
        
        print(f"Database initialized at: {DB_PATH}")

def execute_query(query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
    """Execute a SELECT query and return results"""
    with get_db() as conn:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.fetchall()

def execute_insert(query: str, params: Tuple) -> int:
    """Execute an INSERT query and return the last row id"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.lastrowid

def execute_many(query: str, params_list: List[Tuple]) -> int:
    """Execute multiple INSERT queries"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.executemany(query, params_list)
        return cursor.rowcount

def execute_update(query: str, params: Tuple) -> int:
    """Execute an UPDATE query and return affected rows"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.rowcount