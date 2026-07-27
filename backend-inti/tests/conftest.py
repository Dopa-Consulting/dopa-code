"""Fixtures compartidos para tests del AgentLoop."""
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


@pytest_asyncio.fixture
async def test_db(tmp_path, monkeypatch):
    """DB sqlite en memoria temporal para tests de checkpoint."""
    import inti.database as dbmod
    from inti.database import Base

    # Importar TODOS los modelos que tienen tablas
    import inti.models.job       # noqa: F401
    import inti.models.diff      # noqa: F401
    import inti.models.job_step  # noqa: F401
    import inti.models.approval  # noqa: F401
    import inti.models.event     # noqa: F401
    import inti.models.audit_log # noqa: F401
    import inti.models.ci_run    # noqa: F401

    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/t.db")
    sess = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(dbmod, "async_session", sess)

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield sess
    await eng.dispose()
