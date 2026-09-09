import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'app.db')}"

engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()


if __name__ == "__main__":
    init_db()
    print("Database initialized. Check the data/ folder for app.db")