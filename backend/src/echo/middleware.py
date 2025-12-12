"""
FastAPI中间件：Bearer Token鉴权
"""
from __future__ import annotations

from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from echo.auth import verify_token


# 无需鉴权的路径（精确匹配）
EXCLUDE_PATHS = {
    "/health",
    "/api/auth/login",
    "/docs",
    "/openapi.json",
    "/redoc",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """Bearer Token鉴权中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 排除不需要鉴权的路径（精确匹配，避免前缀误放行）
        if request.url.path in EXCLUDE_PATHS:
            return await call_next(request)

        # 提取Authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "unauthorized", "detail": "Missing Authorization header"},
            )

        # 检查Bearer前缀
        parts = auth_header.split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "unauthorized", "detail": "Invalid Authorization header format"},
            )

        token = parts[1]

        # 校验Token
        user_info = await verify_token(token)
        if not user_info:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "unauthorized", "detail": "Invalid or expired token"},
            )

        # 注入用户信息到request.state
        request.state.user = user_info

        return await call_next(request)
