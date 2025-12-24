"""
Utterance 数据库操作
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def create_utterance(
    pool: Any,
    lecture_id: int,
    seq: int,
    start_ms: int,
    end_ms: int,
    text_en: str,
    text_zh: str = "",
    source: str = "realtime"
) -> None:
    """
    插入 utterance 记录

    Args:
        pool: psycopg3 连接池
        lecture_id: 讲座 ID
        seq: 序号（单调递增）
        start_ms: 开始时间（毫秒）
        end_ms: 结束时间（毫秒）
        text_en: 英文文本
        text_zh: 中文翻译（可选）
        source: 来源（realtime/reprocess）
    """
    sql = """
        INSERT INTO utterances (lecture_id, seq, start_ms, end_ms, text_en, text_zh, source)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (lecture_id, seq, source) DO NOTHING
    """
    try:
        async with pool.connection() as conn:
            await conn.execute(sql, (lecture_id, seq, start_ms, end_ms, text_en, text_zh, source))
    except Exception as exc:
        logger.error(f"Failed to create utterance: {exc}", exc_info=True)


async def get_max_seq(pool: Any, lecture_id: int, source: str = "realtime") -> int:
    """
    获取指定讲座的最大 seq（用于服务器重启时恢复）

    Args:
        pool: psycopg3 连接池
        lecture_id: 讲座 ID
        source: 来源（realtime/reprocess）

    Returns:
        最大 seq，如果没有记录返回 0
    """
    sql = """
        SELECT COALESCE(MAX(seq), 0) as max_seq
        FROM utterances
        WHERE lecture_id = %s AND source = %s
    """
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, (lecture_id, source))
                row = await cur.fetchone()
                return row[0] if row else 0
    except Exception as exc:
        logger.error(f"Failed to get max seq: {exc}", exc_info=True)
        return 0


async def list_utterances(
    pool: Any,
    lecture_id: int,
    source: str = "realtime",
    limit: int = 1000,
    offset: int = 0
) -> list[dict[str, Any]]:
    """
    查询讲座的历史字幕列表

    Args:
        pool: psycopg3 连接池
        lecture_id: 讲座 ID
        source: 来源（realtime/reprocess）
        limit: 最大返回数量
        offset: 偏移量

    Returns:
        字幕列表 [{"seq": int, "start_ms": int, "end_ms": int, "text_en": str, "text_zh": str|None}, ...]
    """
    sql = """
        SELECT seq, start_ms, end_ms, text_en, text_zh
        FROM utterances
        WHERE lecture_id = %s AND source = %s
        ORDER BY seq ASC
        LIMIT %s OFFSET %s
    """
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, (lecture_id, source, limit, offset))
                rows = await cur.fetchall()
                return [
                    {
                        "seq": row[0],
                        "start_ms": row[1],
                        "end_ms": row[2],
                        "text_en": row[3],
                        "text_zh": row[4],
                    }
                    for row in rows
                ]
    except Exception as exc:
        logger.error(f"Failed to list utterances: {exc}", exc_info=True)
        return []


async def update_translation(
    pool: Any,
    lecture_id: int,
    seq: int,
    text_zh: str,
    source: str = "realtime"
) -> None:
    """
    更新字幕的中文翻译（异步翻译完成后调用）

    Args:
        pool: psycopg3 连接池
        lecture_id: 讲座 ID
        seq: 序号
        text_zh: 中文翻译
        source: 来源（realtime/reprocess）
    """
    sql = """
        UPDATE utterances
        SET text_zh = %s
        WHERE lecture_id = %s AND seq = %s AND source = %s
    """
    try:
        async with pool.connection() as conn:
            await conn.execute(sql, (text_zh, lecture_id, seq, source))
            logger.debug(f"Updated translation for lecture {lecture_id} seq {seq}")
    except Exception as exc:
        logger.error(f"Failed to update translation: {exc}", exc_info=True)
