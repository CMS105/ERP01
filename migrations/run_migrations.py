import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import engine
from app.config import settings

def run_migrations():
    print(f"Connecting to database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
    migrations_dir = Path(__file__).parent
    sql_files = sorted(migrations_dir.glob("*.sql"))

    with engine.begin() as conn:
        for sql_file in sql_files:
            print(f"Applying migration: {sql_file.name}...")
            content = sql_file.read_text(encoding="utf-8")
            # Execute migration statements
            conn.execute(text(content))
            print(f"Successfully applied {sql_file.name}")

if __name__ == "__main__":
    run_migrations()
