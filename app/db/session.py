"""Async SQLAlchemy engine + session for the crawler Postgres DB.

PriceHub connects as ``partner_api_usr`` — SELECT-only on the price/news data
schemas, and INSERT/UPDATE only on ``partner_schm`` (partner keys + usage). See
migrations/partner/R001__grants.sql for the exact privileges.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# URL.create safely handles special characters in the password (e.g. '@').
DATABASE_URL = URL.create(
    "postgresql+asyncpg",
    username=settings.PARTNER_DB_USER,
    password=settings.PARTNER_DB_PASSWORD,
    host=settings.DB_HOST,
    port=settings.DB_PORT,
    database=settings.DB_NAME,
)

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True, echo=False)

SessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields a session, closed automatically."""
    async with SessionLocal() as session:
        yield session
