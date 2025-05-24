# migrate_database.py
"""
Database migration script to add the updated_in_automate and completed_at columns
to existing SQLite databases.

Run this script once to update your existing database schema.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = 'database.db'

def migrate_database():
    """Add new columns to existing database"""
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found. Nothing to migrate.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(workstations)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add updated_in_automate column if it doesn't exist
        if 'updated_in_automate' not in columns:
            print("Adding updated_in_automate column...")
            cursor.execute("""
                ALTER TABLE workstations 
                ADD COLUMN updated_in_automate BOOLEAN DEFAULT 0
            """)
            print("✓ Column updated_in_automate added successfully!")
        else:
            print("Column updated_in_automate already exists.")
        
        # Add completed_at column if it doesn't exist
        if 'completed_at' not in columns:
            print("Adding completed_at column...")
            cursor.execute("""
                ALTER TABLE workstations 
                ADD COLUMN completed_at DATETIME
            """)
            print("✓ Column completed_at added successfully!")
            
            # Update completed_at for existing completed workstations
            print("Setting completed_at for existing completed workstations...")
            cursor.execute("""
                UPDATE workstations 
                SET completed_at = ? 
                WHERE status = 'Completed' AND completed_at IS NULL
            """, (datetime.utcnow(),))
            affected_rows = cursor.rowcount
            print(f"✓ Updated {affected_rows} completed workstations with timestamp.")
        else:
            print("Column completed_at already exists.")
        
        conn.commit()
        print("\nMigration completed successfully!")
        
    except sqlite3.Error as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
