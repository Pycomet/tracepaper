import os
from sqlmodel import create_engine, SQLModel, Session

# Define the directory for the database and other data
DATA_DIR = "backend/data"
DATABASE_FILE = "tracepaper.db"
DATABASE_PATH = os.path.join(DATA_DIR, DATABASE_FILE)

# Ensure the data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(DATABASE_URL, echo=True) # echo=True for logging SQL queries, can be False in prod

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session 