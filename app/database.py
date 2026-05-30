import os
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv

# =========================================================================
# 1. ENVIRONMENT ENVIRONMENT VARIABLES CONFIGURATION
# =========================================================================
# Load environment variables from a .env file if it exists.
# In a local development environment, python-dotenv facilitates frictionless configuration.
# In containerized/production environments (e.g., Docker, Kubernetes), this gracefully
# defers to the environment variables injected into the shell.
load_dotenv()

# PostgreSQL is the primary enterprise-grade database. We fall back to standard SQLite
# only for developer workflow convenience and offline unit-testing suites.
DEFAULT_FALLBACK_DB = "sqlite:///./store_intelligence.db"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_FALLBACK_DB)

# =========================================================================
# 2. DATABASE ENGINE INITIALIZATION & POOL TUNING
# =========================================================================
logger.info(f"Initializing database engine. Configured URL scheme: {DATABASE_URL.split('://')[0]}://...")

if DATABASE_URL.startswith("postgresql"):
    # Production-grade PostgreSQL Connection Pool settings:
    # - pool_size: Maximum of 20 active persistent connections kept open.
    # - max_overflow: Up to 10 additional transient connections if pool limits are reached.
    # - pool_recycle: Recycle connections older than 30 minutes (1800s) to prevent idle timeouts.
    # - pool_pre_ping: Pre-pings server with 'SELECT 1' before checkout to ensure connection integrity.
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=int(os.getenv("DB_POOL_SIZE", "20")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
        pool_pre_ping=True
    )
    logger.info("Database engine established with robust PostgreSQL connection pooling (QueuePool).")
else:
    # Local developer SQLite engine.
    # - check_same_thread: False is mandatory to allow multiple async FastAPI request threads
    #   to share the same SQLite database session without throwing threading assertion exceptions.
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    logger.warning("Database engine established using local SQLite fallback database. Connection pooling bypassed.")

# =========================================================================
# 3. SESSION & ORM DECLARATIVE BASE
# =========================================================================
# Create a thread-safe database session factory.
# - autocommit=False: Prevents transactions from committing automatically (requires db.commit()).
# - autoflush=False: Defer object flushing to the database until explicitly requested or committed.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all SQLAlchemy Declarative ORM models.
Base = declarative_base()

# =========================================================================
# 4. DEPENDENCY INJECTION GENERATOR FOR FASTAPI
# =========================================================================
def get_db():
    """
    FastAPI dependency injection generator that yields a new SQLAlchemy Session per HTTP request.
    
    Guarantees session closure at the end of the request lifecycle, ensuring connections
    are properly returned back to the QueuePool or cleaned up, preventing connection leaks.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
