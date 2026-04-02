from sqlmodel import create_engine, SQLModel, Session
from pathlib import Path

# Need to import all SQLModel classes so they are registered before create_all
from models.domain import Project, Resource, Chat, Message  # noqa: F401

DATA_DIR = Path.home() / "rubberduck"
DB_PATH = DATA_DIR / "rubberduck.db"

sqlite_url = f"sqlite:///{DB_PATH}"

# connect_args={"check_same_thread": False} is needed for SQLite in FastAPI
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})


def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
