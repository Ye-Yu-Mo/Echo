"""
认证与鉴权模块

提供：
- login(): 用户名密码登录，返回Token
- verify_token(): 校验Token，返回用户信息
"""
from __future__ import annotations

import secrets
from typing import Any

import bcrypt
from psycopg import AsyncConnection

from echo.db import get_conn


async def login(username: str, password: str) -> dict[str, Any] | None:
    """
    用户名密码登录

    返回 {"user_id": int, "username": str, "role": str, "token": str}
    或 None（登录失败）
    """
    # 假hash，防时序侧信道枚举用户名
    fake_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5sDovXxP0CuKa"

    async for conn in get_conn():
        # 查询用户
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, username, password_hash, role, disabled_at
                FROM users
                WHERE username = %s
                """,
                (username,),
            )
            row = await cur.fetchone()

        # 始终执行bcrypt校验，防时序攻击
        password_hash = row[2] if row else fake_hash
        if not bcrypt.checkpw(password.encode(), password_hash.encode()):
            return None

        # 用户不存在或已禁用
        if not row or row[4] is not None:
            return None

        user_id, username, _, role, _ = row

        # 生成新Token（32字节随机串，hex编码）
        token = secrets.token_hex(32)

        # 更新用户Token
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE users SET token = %s WHERE id = %s",
                (token, user_id),
            )
            await conn.commit()

        return {
            "user_id": user_id,
            "username": username,
            "role": role,
            "token": token,
        }


async def verify_token(token: str) -> dict[str, Any] | None:
    """
    校验Token，返回用户信息

    返回 {"user_id": int, "username": str, "role": str}
    或 None（Token无效）
    """
    async for conn in get_conn():
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, username, role
                FROM users
                WHERE token = %s AND disabled_at IS NULL
                """,
                (token,),
            )
            row = await cur.fetchone()

        if not row:
            return None

        user_id, username, role = row
        return {
            "user_id": user_id,
            "username": username,
            "role": role,
        }


async def logout(token: str) -> bool:
    """
    登出（清除Token）

    返回 True（成功）或 False（Token不存在）
    """
    async for conn in get_conn():
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE users SET token = NULL WHERE token = %s",
                (token,),
            )
            await conn.commit()
            return cur.rowcount > 0
