"""
Database wiring. Uses SQLite by default (a single file, zero setup —
fine for an MVP), but DATABASE_URL can point to Postgres/Supabase
later without changing any other file.

Note: on most free hosts (Render's free tier included) local disk is
wiped on redeploy, so a SQLite file won't survive that. Once you have
real paying users, switch DATABASE_URL to a hosted Postgres (Supabase
has a free tier) so accounts and subscriptions persist.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
