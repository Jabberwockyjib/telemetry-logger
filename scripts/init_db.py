#!/usr/bin/env python3
"""Database initialization script.

This script creates the database tables using Alembic migrations.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import create_async_engine

from backend.app.config import settings
from backend.app.db.base import Base


async def init_db() -> None:
    """Initialize database by creating all tables.
    
    This creates tables directly using SQLAlchemy metadata.
    For production use, prefer running Alembic migrations.
    """
    print(f"Initializing database: {settings.database_url}")
    
    # Create async engine
    engine = create_async_engine(settings.database_url, echo=True)
    
    try:
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Database initialized successfully!")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        sys.exit(1)
    
    finally:
        await engine.dispose()


async def run_migrations() -> None:
    """Run Alembic migrations to initialize database.
    
    This is the preferred method for database initialization.
    """
    import subprocess
    
    print("Running Alembic migrations...")
    
    try:
        # Run alembic upgrade
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True,
        )
        
        print("✅ Migrations applied successfully!")
        if result.stdout:
            print(result.stdout)
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running migrations: {e}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize database")
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="Use Alembic migrations instead of direct table creation",
    )
    
    args = parser.parse_args()
    
    if args.migrate:
        asyncio.run(run_migrations())
    else:
        asyncio.run(init_db())


if __name__ == "__main__":
    main()
