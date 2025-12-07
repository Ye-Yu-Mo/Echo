from __future__ import annotations

import asyncio
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect


app = FastAPI(title="Echo Backend", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.websocket("/ws/lectures/{lecture_id}")
async def lecture_socket(websocket: WebSocket, lecture_id: str) -> None:
    # TODO: add token auth and room/session management
    await websocket.accept()
    try:
        while True:
            frame = await websocket.receive_bytes()
            # Echo placeholder; replace with Whisper → translate → broadcast pipeline
            await websocket.send_json(
                {
                    "type": "subtitle",
                    "lecture_id": lecture_id,
                    "seq": 0,
                    "start_ms": 0,
                    "end_ms": 0,
                    "text_en": f"bytes:{len(frame)}",
                    "text_zh": "占位翻译",
                }
            )
            await asyncio.sleep(0)
    except WebSocketDisconnect:
        return
    except Exception as exc:  # pragma: no cover - placeholder error path
        await websocket.close(code=1011, reason=str(exc))


def create_app() -> FastAPI:
    return app
