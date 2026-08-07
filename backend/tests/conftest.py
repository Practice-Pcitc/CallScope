import os

import pytest

# Tests must never create or drop tables in the developer's callscope.db.
os.environ["CALLSCOPE_DATABASE_URL"] = "sqlite://"

from app.core.database import engine
from app.models import Base


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session", autouse=True)
def dispose_database_engine():
    """测试结束后显式释放 SQLite 连接，避免 Windows 句柄延迟退出。"""
    yield
    engine.dispose()
