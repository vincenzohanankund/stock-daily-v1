# -*- coding: utf-8 -*-
"""Authentication service for single admin user."""

from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass
from typing import Dict

from src.config import Config, setup_env
from src.core.config_manager import ConfigManager


class AuthServiceError(Exception):
    """Base error for auth service."""


class PasswordNotInitializedError(AuthServiceError):
    """Raised when password has not been set yet."""


class PasswordAlreadyInitializedError(AuthServiceError):
    """Raised when trying to setup password twice."""


class InvalidCredentialsError(AuthServiceError):
    """Raised when credential validation fails."""


@dataclass(frozen=True)
class AuthStatus:
    """Auth status for UI bootstrap."""

    username: str
    password_initialized: bool

    @property
    def requires_password_setup(self) -> bool:
        return not self.password_initialized


class AuthService:
    """Handle first-time password setup and password reset."""

    USERNAME_KEY = "WEB_ADMIN_USERNAME"
    PASSWORD_HASH_KEY = "WEB_ADMIN_PASSWORD_HASH"
    DEFAULT_USERNAME = "admin"
    HASH_ALGORITHM = "pbkdf2_sha256"
    HASH_ITERATIONS = 260000

    def __init__(self):
        self._config_manager = ConfigManager()

    def get_status(self) -> Dict[str, object]:
        """Return authentication setup status."""
        status = self._build_status()
        return {
            "username": status.username,
            "password_initialized": status.password_initialized,
            "requires_password_setup": status.requires_password_setup,
        }

    def login(self, username: str, password: str) -> Dict[str, object]:
        """Validate username/password for login."""
        normalized_username = self._normalize_username(username)
        status = self._build_status()
        if status.requires_password_setup:
            raise PasswordNotInitializedError("系统尚未设置登录密码，请先完成首次密码设置")

        if normalized_username != status.username:
            raise InvalidCredentialsError("用户名或密码错误")

        password_hash = self._read_password_hash()
        if not self._verify_password(password, password_hash):
            raise InvalidCredentialsError("用户名或密码错误")

        return {
            "success": True,
            "username": status.username,
            "message": "登录成功",
        }

    def setup_password(self, username: str, password: str, confirm_password: str) -> Dict[str, object]:
        """Set initial password when no password exists."""
        normalized_username = self._normalize_username(username)
        status = self._build_status()
        if status.password_initialized:
            raise PasswordAlreadyInitializedError("密码已设置，请使用修改密码接口")

        self._ensure_password_valid(password, confirm_password)
        password_hash = self._hash_password(password)
        self._persist_credentials(normalized_username, password_hash)

        return {
            "success": True,
            "username": normalized_username,
            "message": "首次密码设置成功",
        }

    def reset_password_from_server(
        self,
        username: str,
        new_password: str,
        confirm_password: str,
    ) -> Dict[str, object]:
        """Reset password directly from server-side trusted environment."""
        normalized_username = self._normalize_username(username)
        self._ensure_password_valid(new_password, confirm_password)

        password_hash = self._hash_password(new_password)
        self._persist_credentials(normalized_username, password_hash)

        return {
            "success": True,
            "username": normalized_username,
            "message": "服务器侧密码重置成功",
        }

    def reset_password(
        self,
        username: str,
        current_password: str,
        new_password: str,
        confirm_password: str,
    ) -> Dict[str, object]:
        """Reset password with current password verification."""
        normalized_username = self._normalize_username(username)
        status = self._build_status()
        if status.requires_password_setup:
            raise PasswordNotInitializedError("系统尚未设置登录密码，请先完成首次密码设置")

        if normalized_username != status.username:
            raise InvalidCredentialsError("用户名或密码错误")

        password_hash = self._read_password_hash()
        if not self._verify_password(current_password, password_hash):
            raise InvalidCredentialsError("用户名或密码错误")

        self._ensure_password_valid(new_password, confirm_password)
        if current_password == new_password:
            raise ValueError("新密码不能与当前密码相同")

        new_hash = self._hash_password(new_password)
        self._persist_credentials(normalized_username, new_hash)

        return {
            "success": True,
            "username": normalized_username,
            "message": "密码重置成功",
        }

    def _build_status(self) -> AuthStatus:
        config_map = self._config_manager.read_config_map()
        configured_username = (config_map.get(self.USERNAME_KEY, "") or "").strip().lower()
        username = configured_username or self.DEFAULT_USERNAME
        password_hash = (config_map.get(self.PASSWORD_HASH_KEY, "") or "").strip()
        return AuthStatus(username=username, password_initialized=bool(password_hash))

    def _read_password_hash(self) -> str:
        config_map = self._config_manager.read_config_map()
        return (config_map.get(self.PASSWORD_HASH_KEY, "") or "").strip()

    def _persist_credentials(self, username: str, password_hash: str) -> None:
        self._config_manager.apply_updates(
            updates=[
                (self.USERNAME_KEY, username),
                (self.PASSWORD_HASH_KEY, password_hash),
            ],
            sensitive_keys={self.PASSWORD_HASH_KEY},
            mask_token="******",
        )

        Config.reset_instance()
        setup_env(override=True)

    def _normalize_username(self, username: str) -> str:
        normalized = (username or "").strip().lower()
        if not normalized:
            normalized = self.DEFAULT_USERNAME

        if normalized != self.DEFAULT_USERNAME:
            raise ValueError("当前版本仅支持 admin 用户")

        return normalized

    def _ensure_password_valid(self, password: str, confirm_password: str) -> None:
        if password != confirm_password:
            raise ValueError("两次输入的密码不一致")

        if len(password) < 8:
            raise ValueError("密码长度至少 8 位")

        if len(password) > 128:
            raise ValueError("密码长度不能超过 128 位")

        if "\n" in password or "\r" in password:
            raise ValueError("密码不能包含换行符")

    def _hash_password(self, password: str) -> str:
        salt = os.urandom(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            self.HASH_ITERATIONS,
        )
        return f"{self.HASH_ALGORITHM}${self.HASH_ITERATIONS}${salt.hex()}${digest.hex()}"

    @classmethod
    def _verify_password(cls, password: str, encoded_hash: str) -> bool:
        try:
            algorithm, iterations_raw, salt_hex, digest_hex = encoded_hash.split("$", 3)
            if algorithm != cls.HASH_ALGORITHM:
                return False

            iterations = int(iterations_raw)
            salt = bytes.fromhex(salt_hex)
            expected_digest = bytes.fromhex(digest_hex)
        except (TypeError, ValueError):
            return False

        actual_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(actual_digest, expected_digest)
