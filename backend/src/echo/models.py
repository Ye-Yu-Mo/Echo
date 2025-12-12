"""
Pydantic模型定义
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# 登录请求
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1)


# Token响应
class TokenResponse(BaseModel):
    token: str
    user_id: int
    username: str
    role: str


# 用户信息
class UserInfo(BaseModel):
    user_id: int
    username: str
    role: str


# 创建讲座请求
class CreateLectureRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


# 讲座信息
class LectureInfo(BaseModel):
    id: int
    title: str
    creator_id: int
    status: str  # init|recording|summarizing|done
    created_at: datetime
    ended_at: datetime | None
