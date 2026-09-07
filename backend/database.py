from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

DATABASE_URL = "sqlite:///./data/app.db"

engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()

if __name__ == "__main__":
    init_db()
    print("Database initialized. Check the data/ folder for app.db")