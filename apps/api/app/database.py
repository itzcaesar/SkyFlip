from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import get_settings
from .models import Base

settings = get_settings()
if settings.database_url.startswith("sqlite") and ":memory:" not in settings.database_url:
    sqlite_path = settings.database_url.partition("///")[2]
    if sqlite_path:
        Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def check_database() -> tuple[bool, str | None]:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:  # health endpoints must report, not hide, infrastructure failures
        return False, type(exc).__name__


async def ensure_local_schema() -> None:
    """Create the local SQLite schema automatically; production still uses Alembic."""

    if not settings.database_url.startswith("sqlite") or not settings.auto_create_schema:
        return
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
