"""SQLAlchemy 2.0 Database configuration (Async + Sync support)."""

from typing import AsyncGenerator, Generator
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker
from app.core.config import settings
from app.core.logging import logger

# ------------------------------------------------------------------------------
# 1. Asynchronous Engine & Session Factory (FastAPI Endpoints)
# ------------------------------------------------------------------------------
is_sqlite_async = settings.DATABASE_URL.startswith("sqlite")

async_connect_args = {"check_same_thread": False} if is_sqlite_async else {}

async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    connect_args=async_connect_args,
    pool_pre_ping=True,
)

# Enable Foreign Key enforcement in SQLite for async connections
if is_sqlite_async:
    @event.listens_for(async_engine.sync_engine, "connect")
    def set_async_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for async FastAPI endpoints."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ------------------------------------------------------------------------------
# 2. Synchronous Engine & Session Factory (Seeding, Migrations, Background Scripts)
# ------------------------------------------------------------------------------
is_sqlite_sync = settings.SYNC_DATABASE_URL.startswith("sqlite")
sync_connect_args = {"check_same_thread": False} if is_sqlite_sync else {}

sync_engine = create_engine(
    settings.SYNC_DATABASE_URL,
    echo=False,
    future=True,
    connect_args=sync_connect_args,
    pool_pre_ping=True,
)

# Enable Foreign Key enforcement in SQLite for sync connections
if is_sqlite_sync:
    @event.listens_for(sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

def get_sync_db() -> Generator[Session, None, None]:
    """Context generator for synchronous jobs & seeding."""
    session = SyncSessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
