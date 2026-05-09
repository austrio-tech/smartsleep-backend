from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()

engine = None
SessionLocal = None

if settings.database_url:
    if settings.database_url.startswith("sqlite"):
        engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    logger.warning("DATABASE_URL not set — SQLAlchemy engine disabled.")


def get_db():
    if SessionLocal is None:
        raise RuntimeError("No DATABASE_URL configured.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
