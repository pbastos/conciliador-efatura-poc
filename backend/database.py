import sqlite3
from contextlib import contextmanager
from typing import List, Dict, Any

DB_PATH = "efatura.db"

def dict_factory(cursor, row):
    """Convert SQLite rows to dictionaries"""
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
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
            document_number TEXT,
            document_date DATE,
            supplier_name TEXT,
            supplier_nif TEXT,
            total_amount REAL,
            tax_amount REAL,
            status TEXT DEFAULT 'unmatched',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Bank movements table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bank_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movement_date DATE,
            description TEXT,
            amount REAL,
            reference TEXT,
            status TEXT DEFAULT 'unmatched',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Matches table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            efatura_id INTEGER NOT NULL,
            bank_id INTEGER NOT NULL,
            confidence_score REAL,
            status TEXT DEFAULT 'proposed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (efatura_id) REFERENCES efatura_records(id),
            FOREIGN KEY (bank_id) REFERENCES bank_movements(id),
            UNIQUE(efatura_id, bank_id)
        )
        """)
        
        # Settings table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Insert default settings if they don't exist
        cursor.execute("""
        INSERT OR IGNORE INTO settings (key, value) VALUES 
        ('confidence_threshold', '70'),
        ('bank_column_date', ''),
        ('bank_column_description', ''),
        ('bank_column_amount', '')
        """)
        
        print("Database initialized successfully")

def query(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Execute a SELECT query and return results"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.fetchall()

def execute(sql: str, params: tuple = ()) -> int:
    """Execute an INSERT/UPDATE/DELETE query and return affected rows"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.lastrowid