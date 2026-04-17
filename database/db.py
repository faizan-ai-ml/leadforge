import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from dotenv import load_dotenv
import yaml
from loguru import logger
from database.models import Base

# Load env variables (for DATABASE_URL)
load_dotenv()

# Load config to check if using SQLite or Postgres
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

DB_TYPE = config.get("db_type", "postgresql")

if DB_TYPE == "sqlite":
    DATABASE_URL = "sqlite:///leadforge.db"
    # SQLite needs special thread logic
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # PostgreSQL expectation. Uses connection pooling natively.
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/leadforge")
    try:
        engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10)
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        engine = None

if engine:
    SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

    def init_db():
        """Creates all tables if they do not exist."""
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database schema initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")

    @contextmanager
    def get_db():
        """Provides a transactional scope around a series of operations."""
        db = SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
else:
    logger.critical("Engine could not be initialized. Please check your DB settings.")
    # Mock implementations to prevent crashing on import
    SessionLocal = None
    def init_db(): pass
    @contextmanager
    def get_db(): yield None
