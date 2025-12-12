from __future__ import annotations

import asyncio
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect, status

from echo.auth import login, logout
from echo.db import close_pool, get_pool
from echo.lectures import create_lecture, end_lecture, get_lecture, list_lectures
from echo.middleware import AuthMiddleware
from echo.models import CreateLectureRequest, LectureInfo, LoginRequest, TokenResponse


app = FastAPI(title="Echo Backend", version="0.1.0")

# 挂载鉴权中间件
app.add_middleware(AuthMiddleware)


@app.on_event("startup")
async def startup() -> None:
    """应用启动时初始化连接池、任务队列和存储目录"""
    from echo.storage import init_storage
    from echo.tasks import start_workers

    get_pool()  # 触发连接池创建
    start_workers(num_workers=2)  # 启动2个worker
    init_storage()  # 初始化存储目录


@app.on_event("shutdown")
async def shutdown() -> None:
    """应用关闭时清理连接池和任务队列"""
    from echo.tasks import stop_workers

    await stop_workers()
    await close_pool()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/login", response_model=TokenResponse)
async def api_login(req: LoginRequest) -> TokenResponse:
    """用户名密码登录"""
    result = await login(req.username, req.password)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    return TokenResponse(**result)


@app.post("/api/auth/logout")
async def api_logout(authorization: str = Header()) -> dict[str, str]:
    """登出（清除Token）"""
    # 提取Bearer token
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Authorization header",
        )

    token = parts[1]
    success = await logout(token)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found",
        )

    return {"message": "Logged out successfully"}


# 讲座管理API

@app.post("/api/lectures", response_model=LectureInfo, status_code=status.HTTP_201_CREATED)
async def api_create_lecture(req: CreateLectureRequest, request: Request) -> LectureInfo:
    """创建讲座"""
    user = request.state.user
    result = await create_lecture(req.title, user["user_id"])
    return LectureInfo(**result)


@app.get("/api/lectures", response_model=list[LectureInfo])
async def api_list_lectures(request: Request, limit: int = 50, offset: int = 0) -> list[LectureInfo]:
    """列出当前用户创建的讲座"""
    user = request.state.user
    results = await list_lectures(user["user_id"], limit, offset)
    return [LectureInfo(**r) for r in results]


@app.get("/api/lectures/{lecture_id}", response_model=LectureInfo)
async def api_get_lecture(lecture_id: int, request: Request) -> LectureInfo:
    """获取讲座详情（仅创建者可见）"""
    result = await get_lecture(lecture_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lecture not found",
        )

    # 权限检查：仅创建者可见
    user = request.state.user
    if result["creator_id"] != user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return LectureInfo(**result)


@app.post("/api/lectures/{lecture_id}/join")
async def api_join_lecture(lecture_id: int, request: Request) -> LectureInfo:
    """加入讲座（仅创建者可加入，后续可扩展为多用户共享）"""
    result = await get_lecture(lecture_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lecture not found",
        )

    # 权限检查：仅创建者可加入（后续可改为允许邀请用户）
    user = request.state.user
    if result["creator_id"] != user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return LectureInfo(**result)


@app.post("/api/lectures/{lecture_id}/end")
async def api_end_lecture(lecture_id: int, request: Request) -> dict[str, str]:
    """结束讲座（仅创建者可操作）"""
    # 先获取讲座检查权限
    result = await get_lecture(lecture_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lecture not found",
        )

    # 权限检查：仅创建者可结束
    user = request.state.user
    if result["creator_id"] != user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    success = await end_lecture(lecture_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lecture not found",
        )
    return {"message": "Lecture ended, summary task triggered"}


@app.websocket("/ws/lectures/{lecture_id}")
async def lecture_socket(websocket: WebSocket, lecture_id: int) -> None:
    """
    讲座实时字幕WebSocket

    鉴权：query参数传token，如 ws://...?token=xxx
    心跳：服务端每30s发ping，客户端应回pong
    """
    from echo.ws import authenticate_ws, broadcast, heartbeat, join_room, leave_room

    await websocket.accept()

    # WS握手鉴权
    user_info = await authenticate_ws(websocket)
    if not user_info:
        await websocket.close(code=1008, reason="Unauthorized: missing or invalid token")
        return

    # 检查讲座是否存在
    lecture = await get_lecture(lecture_id)
    if not lecture:
        await websocket.close(code=1008, reason="Lecture not found")
        return

    # 加入房间
    join_room(lecture_id, websocket)

    # 启动心跳任务
    heartbeat_task = asyncio.create_task(heartbeat(websocket))

    try:
        # 发送欢迎消息
        await websocket.send_json({
            "type": "info",
            "message": f"Connected to lecture {lecture_id}",
            "user": user_info["username"],
        })

        # 接收音频帧（M1实现，现在先echo测试）
        while True:
            data = await websocket.receive()

            # 处理pong响应
            if "text" in data:
                msg = data["text"]
                if msg == "pong":
                    continue  # 忽略pong

            # 处理音频帧（二进制）
            if "bytes" in data:
                frame = data["bytes"]
                # TODO M1: Whisper ASR → 翻译 → 广播字幕
                # 占位：echo测试
                await websocket.send_json({
                    "type": "subtitle",
                    "lecture_id": lecture_id,
                    "seq": 0,
                    "start_ms": 0,
                    "end_ms": 0,
                    "text_en": f"Received {len(frame)} bytes",
                    "text_zh": "占位翻译",
                })

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        await websocket.close(code=1011, reason=str(exc))
    finally:
        # 清理：离开房间，取消心跳
        leave_room(lecture_id, websocket)
        heartbeat_task.cancel()


def create_app() -> FastAPI:
    return app
