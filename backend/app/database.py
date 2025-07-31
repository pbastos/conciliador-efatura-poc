import sqlite3
from contextlib import contextmanager
import os

# Database file path
DB_PATH = "conciliador.db"

def get_db():
    """Get a database connection with dict row factory"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@contextmanager
def get_db_cursor():
    """Context manager for database operations"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_database():
    """Initialize database tables"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Create tables
    cursor.executescript("""
    -- E-fatura records
    CREATE TABLE IF NOT EXISTS efatura (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        issuer TEXT NOT NULL,
        invoice TEXT NOT NULL,
        document_type TEXT,
        issue_date DATE NOT NULL,
        total REAL NOT NULL,
        tax_amount REAL,
        tax_base REAL,
        status TEXT,
        upload_batch_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Bank movements
    CREATE TABLE IF NOT EXISTS bank_movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        movement_date DATE NOT NULL,
        value_date DATE,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        balance REAL,
        reference TEXT,
        upload_batch_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Matching results
    CREATE TABLE IF NOT EXISTS matching_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        efatura_id INTEGER NOT NULL,
        bank_movement_id INTEGER NOT NULL,
        confidence_score REAL NOT NULL,
        match_type TEXT NOT NULL,
        status TEXT DEFAULT 'proposed',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (efatura_id) REFERENCES efatura(id),
        FOREIGN KEY (bank_movement_id) REFERENCES bank_movements(id),
        UNIQUE(efatura_id, bank_movement_id)
    );
    
    -- Upload batches
    CREATE TABLE IF NOT EXISTS upload_batches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        file_type TEXT NOT NULL,
        total_records INTEGER DEFAULT 0,
        processed_records INTEGER DEFAULT 0,
        status TEXT DEFAULT 'processing',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create indexes for better performance
    CREATE INDEX IF NOT EXISTS idx_efatura_date ON efatura(issue_date);
    CREATE INDEX IF NOT EXISTS idx_efatura_total ON efatura(total);
    CREATE INDEX IF NOT EXISTS idx_bank_date ON bank_movements(movement_date);
    CREATE INDEX IF NOT EXISTS idx_bank_amount ON bank_movements(amount);
    CREATE INDEX IF NOT EXISTS idx_matching_efatura ON matching_results(efatura_id);
    CREATE INDEX IF NOT EXISTS idx_matching_bank ON matching_results(bank_movement_id);
    CREATE INDEX IF NOT EXISTS idx_matching_status ON matching_results(status);
    """)
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

# Utility functions for common operations

def insert_efatura_records(records, batch_id):
    """Insert multiple e-fatura records"""
    with get_db_cursor() as cursor:
        cursor.executemany("""
            INSERT INTO efatura (issuer, invoice, document_type, issue_date, 
                                total, tax_amount, tax_base, status, upload_batch_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [(r.get('issuer'), r.get('invoice'), r.get('document_type'), 
               r.get('issue_date'), r.get('total'), r.get('tax_amount'), 
               r.get('tax_base'), r.get('status'), batch_id) for r in records])
        return cursor.rowcount

def insert_bank_movements(records, batch_id):
    """Insert multiple bank movements"""
    with get_db_cursor() as cursor:
        cursor.executemany("""
            INSERT INTO bank_movements (movement_date, value_date, description, 
                                      amount, balance, reference, upload_batch_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [(r.get('movement_date'), r.get('value_date'), r.get('description'),
               r.get('amount'), r.get('balance'), r.get('reference'), batch_id) for r in records])
        return cursor.rowcount

def get_unmatched_efatura():
    """Get e-fatura records without matches"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT e.* FROM efatura e
            LEFT JOIN matching_results m ON e.id = m.efatura_id AND m.status != 'rejected'
            WHERE m.id IS NULL
            ORDER BY e.issue_date DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

def get_unmatched_bank_movements():
    """Get bank movements without matches"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT b.* FROM bank_movements b
            LEFT JOIN matching_results m ON b.id = m.bank_movement_id AND m.status != 'rejected'
            WHERE m.id IS NULL
            ORDER BY b.movement_date DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

def create_match(efatura_id, bank_id, confidence, match_type='automatic'):
    """Create a matching result"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO matching_results (efatura_id, bank_movement_id, confidence_score, match_type)
            VALUES (?, ?, ?, ?)
        """, (efatura_id, bank_id, confidence, match_type))
        return cursor.lastrowid

def update_match_status(match_id, status):
    """Update match status (proposed/confirmed/rejected)"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            UPDATE matching_results SET status = ? WHERE id = ?
        """, (status, match_id))
        return cursor.rowcount > 0