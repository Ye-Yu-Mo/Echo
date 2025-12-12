"""
WebSocket房间管理与心跳机制
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

from echo.auth import verify_token


# lecture_id → set of WebSocket连接
_rooms: dict[int, set[WebSocket]] = defaultdict(set)


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


def join_room(lecture_id: int, websocket: WebSocket) -> None:
    """加入讲座房间"""
    _rooms[lecture_id].add(websocket)


def leave_room(lecture_id: int, websocket: WebSocket) -> None:
    """离开讲座房间"""
    _rooms[lecture_id].discard(websocket)
    # 如果房间为空，清理字典
    if not _rooms[lecture_id]:
        del _rooms[lecture_id]


async def broadcast(lecture_id: int, message: dict[str, Any], exclude: WebSocket | None = None) -> None:
    """
    向讲座房间广播消息

    exclude: 排除的连接（通常是发送方自己）
    """
    room = _rooms.get(lecture_id)
    if not room:
        return

    # 收集失败的连接（断线）
    dead_connections = []

    for ws in room:
        if ws is exclude:
            continue
        try:
            await ws.send_json(message)
        except Exception:
            dead_connections.append(ws)

    # 清理断线连接
    for ws in dead_connections:
        leave_room(lecture_id, ws)


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
