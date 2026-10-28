from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_URL

engine = create_engine(DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def query_df(sql: str, params: dict = None):
    """Exécute une requête SQL et retourne un DataFrame pandas."""
    import pandas as pd
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        return pd.DataFrame(result.fetchall(), columns=result.keys())
