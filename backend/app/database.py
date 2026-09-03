import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings

logger = logging.getLogger("earnx.database")

db_url = settings.sync_database_url

# Configure connect args and connection pool
connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    engine = create_engine(db_url, connect_args=connect_args)
else:
    # Attempt connecting to PostgreSQL
    try:
        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_recycle=300,
            pool_size=10,
            max_overflow=20,
            connect_args={"connect_timeout": 5}
        )
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Successfully connected to primary database: %s", engine.url.host)
    except Exception as e:
        logger.warning(
            "Primary database connection failed (%s). Falling back to local SQLite for development.",
            str(e)
        )
        db_url = "sqlite:///./earnx.db"
        connect_args = {"check_same_thread": False}
        engine = create_engine(db_url, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI database session dependency with auto-closing."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables in the connected database if they do not exist."""
    import app.models  # Ensure all models are registered with Base
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema synchronized.")
