"""SQLAlchemy 同步基础设施。

仅负责创建 Engine、Session factory，并暴露 Base。
不在此处执行任何建表、查询或连接操作；import 时无副作用。
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import DATABASE_URL

# 同步 Engine：psycopg (DBAPI) 由 DATABASE_URL 的 scheme 决定（postgresql+psycopg）
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

# Session 工厂，调用方负责关闭
SessionLocal = sessionmaker(bind=engine, class_=Session, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """所有 ORM 模型的声明基类。"""
    pass


def get_db() -> Generator[Session, None, None]:
    """请求级 Session：提供数据库会话，请求结束后关闭。

    仅用于读操作：不 commit、不吞异常。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
