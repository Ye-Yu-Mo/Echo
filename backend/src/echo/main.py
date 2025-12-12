from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 加载 .env 文件（必须在其他导入之前）
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass

from fastapi import FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

from echo.auth import login, logout
from echo.db import close_pool, get_pool
from echo.lectures import create_lecture, end_lecture, get_lecture, list_lectures
from echo.middleware import AuthMiddleware
from echo.models import CreateLectureRequest, LectureInfo, LoginRequest, TokenResponse


app = FastAPI(title="Echo Backend", version="0.1.0")

# CORS 配置（开发环境）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载鉴权中间件
app.add_middleware(AuthMiddleware)


@app.on_event("startup")
async def startup() -> None:
    """应用启动时初始化连接池、任务队列、存储目录和 ASR"""
    from echo.asr import init_asr
    from echo.storage import init_storage
    from echo.tasks import start_workers

    get_pool()  # 触发连接池创建
    start_workers(num_workers=2)  # 启动2个worker
    init_storage()  # 初始化存储目录
    init_asr()  # 初始化 Whisper 模型


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


@app.get("/api/lectures/{lecture_id}/utterances")
async def api_get_utterances(
    lecture_id: int,
    request: Request,
    source: str = "realtime",
    limit: int = 1000,
    offset: int = 0
) -> list[dict[str, Any]]:
    """获取讲座的历史字幕列表（仅创建者可见）"""
    from echo.utterances import list_utterances

    # 检查讲座是否存在
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

    # 查询字幕列表
    pool = get_pool()
    utterances = await list_utterances(pool, lecture_id, source, limit, offset)

    # 转换为与 WebSocket 消息一致的格式
    return [
        {
            "type": "subtitle",
            "lecture_id": lecture_id,
            "seq": u["seq"],
            "start_ms": u["start_ms"],
            "end_ms": u["end_ms"],
            "text_en": u["text_en"],
            "text_zh": u["text_zh"],
        }
        for u in utterances
    ]


@app.websocket("/ws/lectures/{lecture_id}")
async def lecture_socket(websocket: WebSocket, lecture_id: int) -> None:
    """
    讲座实时字幕WebSocket

    鉴权：query参数传token，如 ws://...?token=xxx
    心跳：服务端每30s发ping，客户端应回pong
    消息格式：
      - 入站：二进制PCM帧（16kHz mono int16）或文本"pong"
      - 出站：{type:'info'|'subtitle'|'error'|'ping', ...}
    """
    from echo.asr import transcribe
    from echo.tasks import submit_task
    from echo.translate import translate_text
    from echo.utterances import create_utterance
    from echo.ws import authenticate_ws, broadcast, heartbeat, init_seq_counter, join_room, leave_room, next_seq

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

    # 权限检查：仅创建者可加入（M1暂不支持多用户）
    if lecture["creator_id"] != user_info["user_id"]:
        await websocket.close(code=1008, reason="Access denied")
        return

    # 初始化 seq 计数器（从 DB 恢复）
    pool = get_pool()
    await init_seq_counter(lecture_id, pool)

    # 加入房间
    await join_room(lecture_id, websocket)

    # 启动心跳任务
    heartbeat_task = asyncio.create_task(heartbeat(websocket))

    # 时间戳累加器（用于生成 start_ms/end_ms）
    cumulative_ms = 0

    try:
        # 发送欢迎消息
        await websocket.send_json({
            "type": "info",
            "message": f"Connected to lecture {lecture_id}",
            "user": user_info["username"],
        })

        # 接收音频帧并处理
        while True:
            data = await websocket.receive()

            # 处理pong响应
            if "text" in data:
                msg = data["text"]
                if msg == "pong":
                    continue

            # 处理音频帧（二进制）
            if "bytes" in data:
                frame = data["bytes"]

                # ASR 转录
                result = await transcribe(frame)

                # 处理错误
                if result.get("code") == 2001:
                    await websocket.send_json({
                        "type": "error",
                        "code": 2001,
                        "message": result.get("error", "ASR failed")
                    })
                    continue

                # 静音/无内容，跳过
                text_en = result.get("text", "")
                if not text_en:
                    continue

                # 翻译成中文（M2）
                translate_result = await translate_text(text_en)
                text_zh = translate_result.get("text", "")

                # 处理翻译错误（不阻塞流程，仅记录）
                if translate_result.get("code") == 3001:
                    logger.warning(f"Translation failed: {translate_result.get('error')}")

                # 生成 seq
                seq = await next_seq(lecture_id)

                # 计算时间戳（假设每帧 1s，实际应从音频长度计算）
                frame_duration_ms = len(frame) // 32  # 16kHz mono int16 = 32 bytes/ms
                start_ms = cumulative_ms
                end_ms = cumulative_ms + frame_duration_ms
                cumulative_ms = end_ms

                # 广播双语字幕
                subtitle_msg = {
                    "type": "subtitle",
                    "lecture_id": lecture_id,
                    "seq": seq,
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "text_en": text_en,
                    "text_zh": text_zh,
                }
                await broadcast(lecture_id, subtitle_msg)

                # 异步落库（不阻塞）
                submit_task(create_utterance, pool, lecture_id, seq, start_ms, end_ms, text_en, text_zh, source="realtime")

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error(f"WebSocket error: {exc}", exc_info=True)
        try:
            await websocket.close(code=1011, reason=str(exc))
        except Exception:
            pass  # 连接可能已关闭
    finally:
        # 清理：离开房间，取消心跳
        await leave_room(lecture_id, websocket)
        heartbeat_task.cancel()


def create_app() -> FastAPI:
    return app
