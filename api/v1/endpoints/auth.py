# -*- coding: utf-8 -*-
"""Authentication endpoints for web login."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from api.v1.schemas.auth import (
    AuthStatusResponse,
    LoginRequest,
    LoginResponse,
    PasswordMutationResponse,
    SetupPasswordRequest,
    ChangePasswordRequest,
)
from api.v1.schemas.common import ErrorResponse
from src.services.auth_service import (
    AuthService,
    InvalidCredentialsError,
    PasswordAlreadyInitializedError,
    PasswordNotInitializedError,
)
from src.services.jwt_auth_service import JwtAuthService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/status",
    response_model=AuthStatusResponse,
    responses={
        200: {"description": "Auth status loaded"},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Get auth status",
    description="Return whether admin password has been initialized.",
)
def get_auth_status() -> AuthStatusResponse:
    """Get current authentication status for first-login flow."""
    try:
        payload = AuthService().get_status()
        return AuthStatusResponse(**payload)
    except Exception as exc:
        logger.error("Failed to load auth status: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "获取登录状态失败",
            },
        )


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        200: {"description": "Login success"},
        400: {"description": "Invalid request", "model": ErrorResponse},
        401: {"description": "Invalid credentials", "model": ErrorResponse},
        428: {"description": "Password not initialized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Admin login",
    description="Login with admin username and password.",
)
def login(request: LoginRequest) -> LoginResponse:
    """Validate login credentials."""
    service = AuthService()
    try:
        payload = service.login(username=request.username, password=request.password)
        token_payload = JwtAuthService().issue_token(username=payload["username"])
        payload.update(token_payload)
        return LoginResponse(**payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_error",
                "message": str(exc),
            },
        )
    except PasswordNotInitializedError as exc:
        raise HTTPException(
            status_code=428,
            detail={
                "error": "password_not_initialized",
                "message": str(exc),
            },
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "invalid_credentials",
                "message": str(exc),
            },
        )
    except Exception as exc:
        logger.error("Login failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "登录失败",
            },
        )


@router.post(
    "/change-password",
    response_model=PasswordMutationResponse,
    responses={
        200: {"description": "Password change success"},
        400: {"description": "Invalid request", "model": ErrorResponse},
        401: {"description": "Invalid credentials", "model": ErrorResponse},
        428: {"description": "Password not initialized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Change password",
    description="Change existing password with current password verification.",
)
def change_password(request: Request, payload: ChangePasswordRequest) -> PasswordMutationResponse:
    """Change admin password."""
    service = AuthService()
    try:
        auth_user = getattr(request.state, "auth_user", None)
        if not auth_user:
            raise InvalidCredentialsError("未登录或登录状态无效")

        current_password = (payload.current_password or payload.old_password or "").strip()
        if not current_password:
            raise ValueError("当前密码不能为空")

        result = service.reset_password(
            username=auth_user,
            current_password=current_password,
            new_password=payload.new_password,
            confirm_password=payload.confirm_password,
        )
        result["message"] = "密码修改成功"
        return PasswordMutationResponse(**result)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_error",
                "message": str(exc),
            },
        )
    except PasswordNotInitializedError as exc:
        raise HTTPException(
            status_code=428,
            detail={
                "error": "password_not_initialized",
                "message": str(exc),
            },
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "invalid_credentials",
                "message": str(exc),
            },
        )
    except Exception as exc:
        logger.error("Change password failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "修改密码失败",
            },
        )


@router.post(
    "/setup-password",
    response_model=PasswordMutationResponse,
    responses={
        200: {"description": "Password setup success"},
        400: {"description": "Invalid request", "model": ErrorResponse},
        409: {"description": "Password already initialized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Setup initial password",
    description="Set admin password only when password has not been initialized.",
)
def setup_password(request: SetupPasswordRequest) -> PasswordMutationResponse:
    """Setup admin password for first login."""
    service = AuthService()
    try:
        payload = service.setup_password(
            username=request.username,
            password=request.password,
            confirm_password=request.confirm_password,
        )
        return PasswordMutationResponse(**payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_error",
                "message": str(exc),
            },
        )
    except PasswordAlreadyInitializedError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "password_already_initialized",
                "message": str(exc),
            },
        )
    except Exception as exc:
        logger.error("Setup password failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "设置密码失败",
            },
        )
