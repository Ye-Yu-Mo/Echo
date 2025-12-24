"""
数据库连接池与初始化

提供：
- get_pool(): 获取全局连接池（psycopg3 async pool）
- init_db(): 执行schema.sql初始化表结构
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import AsyncGenerator

import psycopg
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)


_pool: AsyncConnectionPool | None = None


def get_pool() -> AsyncConnectionPool:
    """获取全局连接池，首次调用时创建"""
    global _pool
    if _pool is None:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL environment variable not set")
        _pool = AsyncConnectionPool(
            conninfo=database_url,
            min_size=2,
            max_size=10,
            timeout=30.0,
        )
    return _pool


async def close_pool() -> None:
    """关闭连接池（用于优雅退出）"""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def get_conn() -> AsyncGenerator[AsyncConnection, None]:
    """获取数据库连接（上下文管理器）"""
    pool = get_pool()
    async with pool.connection() as conn:
        yield conn


async def init_db() -> None:
    """
    执行schema.sql初始化数据库表结构

    Raises:
        FileNotFoundError: schema.sql 文件不存在
        RuntimeError: 数据库初始化失败
    """
    schema_path = Path(__file__).parent.parent / "schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"schema.sql not found at {schema_path}")

    sql = schema_path.read_text(encoding="utf-8")

    try:
        async with get_pool().connection() as conn:
            await conn.execute(sql)
            await conn.commit()
            logger.info("Database initialized successfully")
    except psycopg.Error as exc:
        logger.error(f"DB error during init_db: {exc}", exc_info=True)
        raise RuntimeError("Failed to initialize database") from exc
