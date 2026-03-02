"""
Database configuration and session management.

Provides SQLAlchemy engine, session factory, and helper functions for database operations.
"""

import os
from sqlalchemy import create_engine
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
    print("✓ Database initialized successfully")


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
