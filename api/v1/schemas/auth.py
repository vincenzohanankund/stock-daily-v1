# -*- coding: utf-8 -*-
"""Authentication related schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class AuthStatusResponse(BaseModel):
    """Current authentication bootstrap status."""

    username: str = Field(..., description="用户名（当前固定 admin）")
    password_initialized: bool = Field(..., description="是否已设置密码")
    requires_password_setup: bool = Field(..., description="是否需要首次设置密码")


class LoginRequest(BaseModel):
    """Login request payload."""

    username: str = Field("admin", description="用户名，默认 admin")
    password: str = Field(..., min_length=1, description="登录密码")


class LoginResponse(BaseModel):
    """Login response payload."""

    success: bool = Field(True, description="是否登录成功")
    username: str = Field(..., description="用户名")
    message: str = Field(..., description="结果消息")
    access_token: str = Field(..., description="JWT 访问令牌")
    token_type: str = Field("Bearer", description="令牌类型")
    expires_in: int = Field(..., description="令牌有效期（秒）")


class SetupPasswordRequest(BaseModel):
    """First-time password setup request."""

    username: str = Field("admin", description="用户名，默认 admin")
    password: str = Field(..., min_length=1, description="首次设置密码")
    confirm_password: str = Field(..., min_length=1, description="确认密码")


class ChangePasswordRequest(BaseModel):
    """Password change request."""

    current_password: Optional[str] = Field(None, description="当前密码")
    old_password: Optional[str] = Field(None, description="旧密码（兼容字段）")
    new_password: str = Field(..., min_length=1, description="新密码")
    confirm_password: str = Field(..., min_length=1, description="确认新密码")


class PasswordMutationResponse(BaseModel):
    """Password mutation response."""

    success: bool = Field(True, description="是否操作成功")
    username: str = Field(..., description="用户名")
    message: str = Field(..., description="结果消息")
