
import os
from sqlalchemy import create_engine  # pyright: ignore[reportMissingImports]
from sqlalchemy.orm import sessionmaker, declarative_base  # pyright: ignore[reportMissingImports]

DATABASE_URL = "sqlite:///./erp.db"


engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

