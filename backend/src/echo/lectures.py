"""
讲座管理业务逻辑
"""
from __future__ import annotations

from typing import Any

from echo.db import get_conn


async def create_lecture(title: str, creator_id: int) -> dict[str, Any]:
    """
    创建讲座

    返回 {"id": int, "title": str, "creator_id": int, "status": str, "created_at": datetime}
    """
    async for conn in get_conn():
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO lectures (title, creator_id, status)
                VALUES (%s, %s, 'init')
                RETURNING id, title, creator_id, status, created_at, ended_at
                """,
                (title, creator_id),
            )
            row = await cur.fetchone()
            await conn.commit()

        return {
            "id": row[0],
            "title": row[1],
            "creator_id": row[2],
            "status": row[3],
            "created_at": row[4],
            "ended_at": row[5],
        }


async def get_lecture(lecture_id: int) -> dict[str, Any] | None:
    """
    获取讲座详情

    返回讲座信息或None（不存在或已软删除）
    """
    async for conn in get_conn():
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, title, creator_id, status, created_at, ended_at
                FROM lectures
                WHERE id = %s AND deleted_at IS NULL
                """,
                (lecture_id,),
            )
            row = await cur.fetchone()

        if not row:
            return None

        return {
            "id": row[0],
            "title": row[1],
            "creator_id": row[2],
            "status": row[3],
            "created_at": row[4],
            "ended_at": row[5],
        }


async def list_lectures(user_id: int, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    """
    列出用户创建的讲座列表

    返回讲座列表（按创建时间倒序）
    """
    async for conn in get_conn():
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, title, creator_id, status, created_at, ended_at
                FROM lectures
                WHERE creator_id = %s AND deleted_at IS NULL
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (user_id, limit, offset),
            )
            rows = await cur.fetchall()

        return [
            {
                "id": row[0],
                "title": row[1],
                "creator_id": row[2],
                "status": row[3],
                "created_at": row[4],
                "ended_at": row[5],
            }
            for row in rows
        ]


async def update_lecture_status(lecture_id: int, status: str) -> bool:
    """
    更新讲座状态

    返回True（成功）或False（讲座不存在）
    """
    async for conn in get_conn():
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE lectures
                SET status = %s
                WHERE id = %s AND deleted_at IS NULL
                """,
                (status, lecture_id),
            )
            await conn.commit()
            return cur.rowcount > 0


async def end_lecture(lecture_id: int) -> bool:
    """
    结束讲座（设置ended_at，状态改为summarizing）

    返回True（成功）或False（讲座不存在）
    """
    async for conn in get_conn():
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE lectures
                SET status = 'summarizing', ended_at = NOW()
                WHERE id = %s AND deleted_at IS NULL
                """,
                (lecture_id,),
            )
            await conn.commit()
            return cur.rowcount > 0
