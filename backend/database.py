"""
Database configuration and session management.

Provides SQLAlchemy engine, session factory, and helper functions for database operations.
"""

import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool
from database_models import Base

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./listing_agent.db")

# Create engine
# For SQLite, we use StaticPool to handle concurrent requests better
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False  # Set to True for SQL query logging
    )
else:
    # For PostgreSQL/MySQL
    engine = create_engine(DATABASE_URL, echo=False)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Thread-safe session
db_session = scoped_session(SessionLocal)


def init_db():
    """
    Initialize the database by creating all tables.

    This should be called once when the application starts.
    Uses checkfirst=True to avoid errors if tables already exist.
    """
    Base.metadata.create_all(bind=engine, checkfirst=True)
    run_migrations()
    print("✓ Database initialized successfully")


# Additive-only columns to backfill onto pre-existing tables.
# create_all(checkfirst=True) only creates missing TABLES - it never alters
# an existing table's columns, so new nullable columns need this explicit,
# idempotent bootstrap. Safe to run on every startup: existing columns are skipped.
_ADDITIVE_COLUMNS = {
    "product_analyses": [
        ("thumbnail_urls", "JSON"),
    ],
    "draft_listings": [
        ("image_urls", "JSON"),
        ("thumbnail_urls", "JSON"),
        ("ebay_category", "JSON"),
        ("ebay_aspects", "JSON"),
        ("ebay_category_suggestions", "JSON"),
        ("suggested_category_id", "VARCHAR(128)"),
    ],
}


def run_migrations():
    """
    Idempotently ADD COLUMN for any additive columns missing from existing tables.

    Works for both SQLite (local dev) and PostgreSQL (prod/Neon). Never drops or
    alters existing columns/data - only adds new nullable columns.
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    is_sqlite = DATABASE_URL.startswith("sqlite")

    for table_name, columns in _ADDITIVE_COLUMNS.items():
        if table_name not in existing_tables:
            # Table doesn't exist yet (fresh DB) - create_all already built it with
            # the new columns included, nothing to backfill.
            continue

        existing_columns = {col["name"] for col in inspector.get_columns(table_name)}

        for column_name, column_type in columns:
            if column_name in existing_columns:
                continue

            # JSON isn't a native SQLite type; SQLite accepts any type name in
            # ADD COLUMN and stores JSON as TEXT under the hood via SQLAlchemy's
            # JSON type, so this is safe for both dialects.
            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            try:
                with engine.begin() as conn:
                    conn.execute(text(sql))
                print(f"✓ Migration: added column {table_name}.{column_name}")
            except Exception as e:
                # Guard against a race between the initial existence check and the
                # ALTER (e.g. multiple workers starting concurrently) - if the column
                # already exists, that's fine; anything else should surface.
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    continue
                raise


def get_db():
    """
    Dependency function for FastAPI to get a database session.

    Usage in FastAPI endpoint:
        @app.post("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            # use db here
            pass
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def drop_all_tables():
    """
    Drop all tables. USE WITH CAUTION!

    This is primarily for development/testing purposes.
    """
    Base.metadata.drop_all(bind=engine)
    print("⚠️  All tables dropped")


def reset_database():
    """
    Drop all tables and recreate them.

    USE WITH CAUTION - This will delete all data!
    """
    drop_all_tables()
    init_db()
    print("✓ Database reset complete")
