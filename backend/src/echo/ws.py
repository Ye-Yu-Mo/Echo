"""
WebSocket房间管理与心跳机制
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

from echo.auth import verify_token

logger = logging.getLogger(__name__)

# lecture_id → set of WebSocket连接
_rooms: dict[int, set[WebSocket]] = defaultdict(set)

# lecture_id → seq 计数器
_seq_counters: dict[int, int] = {}

# 全局锁（保护 _rooms 和 _seq_counters 的并发修改）
_lock = asyncio.Lock()


async def authenticate_ws(websocket: WebSocket) -> dict[str, Any] | None:
    """
    WebSocket握手鉴权

    从query参数提取token，校验并返回用户信息
    """
    token = websocket.query_params.get("token")
    if not token:
        return None

    user_info = await verify_token(token)
    return user_info


async def init_seq_counter(lecture_id: int, pool: Any) -> None:
    """
    初始化 seq 计数器（从数据库恢复最大值）

    Args:
        lecture_id: 讲座 ID
        pool: 数据库连接池
    """
    from echo.utterances import get_max_seq

    async with _lock:
        if lecture_id not in _seq_counters:
            max_seq = await get_max_seq(pool, lecture_id, source="realtime")
            _seq_counters[lecture_id] = max_seq
            logger.info(f"Initialized seq counter for lecture {lecture_id}: {max_seq}")


async def next_seq(lecture_id: int) -> int:
    """
    获取下一个 seq（线程安全）

    Args:
        lecture_id: 讲座 ID

    Returns:
        新的 seq 值
    """
    async with _lock:
        _seq_counters[lecture_id] = _seq_counters.get(lecture_id, 0) + 1
        return _seq_counters[lecture_id]


async def join_room(lecture_id: int, websocket: WebSocket) -> None:
    """加入讲座房间"""
    async with _lock:
        _rooms[lecture_id].add(websocket)


async def leave_room(lecture_id: int, websocket: WebSocket) -> None:
    """离开讲座房间"""
    async with _lock:
        _rooms[lecture_id].discard(websocket)
        # 如果房间为空，清理字典
        if not _rooms[lecture_id]:
            del _rooms[lecture_id]
            # 清理 seq 计数器（可选，保留也可以）
            _seq_counters.pop(lecture_id, None)


async def broadcast(
    lecture_id: int,
    message: dict[str, Any],
    exclude: WebSocket | None = None,
    timeout: float = 3.0
) -> None:
    """
    向讲座房间广播消息（带超时）

    Args:
        lecture_id: 讲座 ID
        message: 消息内容
        exclude: 排除的连接（通常是发送方自己）
        timeout: 发送超时（秒）
    """
    # 获取当前房间的所有连接（需要加锁获取快照）
    async with _lock:
        room = _rooms.get(lecture_id)
        if not room:
            return
        connections = list(room)

    # 并发发送（带超时）
    async def _send_to_one(ws: WebSocket) -> WebSocket | None:
        if ws is exclude:
            return None
        try:
            await asyncio.wait_for(ws.send_json(message), timeout=timeout)
            return None
        except Exception as exc:
            logger.warning(f"Failed to broadcast to client: {exc}")
            return ws

    # 并发发送所有消息
    dead_connections = await asyncio.gather(
        *[_send_to_one(ws) for ws in connections],
        return_exceptions=True
    )

    # 清理失败的连接
    for ws in dead_connections:
        if isinstance(ws, WebSocket):
            await leave_room(lecture_id, ws)


async def heartbeat(websocket: WebSocket, interval: float = 30.0) -> None:
    """
    心跳检测任务

    每interval秒发送一次ping，客户端应回复pong
    如果发送失败，任务退出（连接已断开）
    """
    try:
        while True:
            await asyncio.sleep(interval)
            await websocket.send_json({"type": "ping"})
    except Exception:
        # 连接已断开，任务退出
        pass
