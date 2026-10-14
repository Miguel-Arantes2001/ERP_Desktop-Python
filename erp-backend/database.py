
from pathlib import Path
from sqlalchemy import create_engine, event  # pyright: ignore[reportMissingImports]
from sqlalchemy.orm import sessionmaker, declarative_base  # pyright: ignore[reportMissingImports]

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "erp.db"

DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

BUSY_TIMEOUT_MS = 5000


engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)


@event.listens_for(engine, "connect")
def _configure_sqlite(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    finally:
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

