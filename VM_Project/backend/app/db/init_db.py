"""Database initialization and safe non-destructive schema migration script."""

import sys
import os
from sqlalchemy import text

backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import sync_engine
from app.core.logging import logger
from app.db.base import Base
import app.db.models  # noqa: F401


def _ensure_sqlite_columns(table_name: str, columns: dict[str, str]) -> None:
    """Safely add missing columns to an existing SQLite table without losing data."""
    with sync_engine.begin() as conn:
        existing_rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
        existing_cols = {row[1] for row in existing_rows}
        for col_name, col_ddl in columns.items():
            if col_name not in existing_cols:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_ddl}"))
                logger.info(f"Migrated {table_name}: added column '{col_name}'.")


def migrate_database_schema() -> None:
    """Idempotent schema migration preserving all existing rows."""
    if not str(sync_engine.url).startswith("sqlite"):
        return

    _ensure_sqlite_columns(
        "customer_attention_items",
        {
            "confidence_level": "VARCHAR(20) DEFAULT 'MEDIUM'",
            "reasoning_summary": "TEXT",
            "identified_risk_factors": "JSON",
            "investigation_steps": "JSON",
            "supporting_evidence": "JSON",
            "data_gaps": "JSON",
        },
    )
    _ensure_sqlite_columns(
        "agent_analysis_runs",
        {
            "iterations_used": "INTEGER NOT NULL DEFAULT 0",
            "tool_calls_count": "INTEGER NOT NULL DEFAULT 0",
            "tool_calls_log": "JSON",
            "degraded_mode": "BOOLEAN NOT NULL DEFAULT 0",
        },
    )


def init_database() -> None:
    """Create all relational tables and apply safe incremental migrations."""
    logger.info("Initializing relational database schema...")
    try:
        Base.metadata.create_all(bind=sync_engine)
        migrate_database_schema()
        table_names = list(Base.metadata.tables.keys())
        logger.info(f"Database ready ({len(table_names)} tables): {', '.join(table_names)}")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


if __name__ == "__main__":
    init_database()
