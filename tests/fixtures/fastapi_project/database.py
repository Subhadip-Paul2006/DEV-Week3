"""Database schema, connection pool, and migrations integration."""

from __future__ import annotations

from datetime import datetime
from typing import Generator

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker

from .config import settings

# Setup SQLAlchemy engine with explicit connection pooling configuration
engine = create_engine(
    settings.db.connection_url,
    pool_size=settings.db.pool_size,
    max_overflow=settings.db.max_overflow,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    """User account model."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="customer")
    created_at = Column(DateTime, default=datetime.utcnow)

    orders = relationship("Order", back_populates="customer")

    __table_args__ = (
        Index("idx_users_email_role", "email", "role"),
    )


class Order(Base):
    """Customer order model."""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(String(30), default="pending", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("User", back_populates="orders")

    __table_args__ = (
        Index("idx_orders_status_created", "status", "created_at"),
    )


def get_db() -> Generator[Session, None, None]:
    """Dependency injection session provider."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_database_migrations() -> None:
    """Run schema migration commands via Alembic."""
    from alembic import command
    from alembic.config import Config
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


def trigger_database_backup() -> bool:
    """Trigger automated snapshot / backup of the database."""
    import subprocess
    cmd = ["pg_dump", "-Fc", "-h", settings.db.host, "-U", settings.db.user, settings.db.name]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except Exception:
        return False
