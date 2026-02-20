# -*- coding: utf-8 -*-
"""JWT issuance and verification with device-bound signing key."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
from pathlib import Path
from typing import Any, Dict

from src.core.config_manager import ConfigManager


class JwtAuthError(Exception):
    """Base JWT auth error."""

    error_code = "invalid_token"


class JwtMissingTokenError(JwtAuthError):
    """Raised when token is missing from request."""

    error_code = "missing_token"


class JwtInvalidTokenError(JwtAuthError):
    """Raised when token format/signature is invalid."""

    error_code = "invalid_token"


class JwtExpiredTokenError(JwtAuthError):
    """Raised when token is expired."""

    error_code = "token_expired"


class JwtAuthService:
    """Issue and verify JWT tokens for API authentication."""

    PRIVATE_KEY_ENV = "JWT_PRIVATE_KEY"
    DEVICE_ID_ENV = "JWT_DEVICE_ID"
    DEVICE_ID_FILE_ENV = "JWT_DEVICE_ID_FILE"
    EXPIRES_MINUTES_ENV = "JWT_EXPIRES_MINUTES"
    ISSUER_ENV = "JWT_ISSUER"
    AUDIENCE_ENV = "JWT_AUDIENCE"

    DEFAULT_ISSUER = "daily_stock_analysis"
    DEFAULT_AUDIENCE = "daily_stock_analysis_web"
    DEFAULT_EXPIRES_MINUTES = 12 * 60
    ALGORITHM = "HS512"

    def __init__(self):
        self._config_manager = ConfigManager()
        self._private_key, self._device_id = self._ensure_key_material()
        self._issuer = os.getenv(self.ISSUER_ENV, self.DEFAULT_ISSUER).strip() or self.DEFAULT_ISSUER
        self._audience = os.getenv(self.AUDIENCE_ENV, self.DEFAULT_AUDIENCE).strip() or self.DEFAULT_AUDIENCE
        self._expires_minutes = self._load_expire_minutes()

    def issue_token(self, username: str) -> Dict[str, Any]:
        """Issue signed JWT token for authenticated user."""
        now = int(time.time())
        exp = now + self._expires_minutes * 60

        payload = {
            "sub": username,
            "iat": now,
            "nbf": now,
            "exp": exp,
            "iss": self._issuer,
            "aud": self._audience,
            "jti": secrets.token_hex(16),
            "did": self._device_id,
        }
        token = self._encode_token(payload)

        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": self._expires_minutes * 60,
        }

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify token signature and claims."""
        if not token:
            raise JwtMissingTokenError("缺少访问令牌")

        parts = token.split(".")
        if len(parts) != 3:
            raise JwtInvalidTokenError("令牌格式不正确")

        header_segment, payload_segment, signature_segment = parts
        signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")

        header = self._decode_segment(header_segment)
        payload = self._decode_segment(payload_segment)

        if not isinstance(header, dict) or header.get("alg") != self.ALGORITHM or header.get("typ") != "JWT":
            raise JwtInvalidTokenError("令牌头无效")

        expected_signature = self._sign(signing_input)
        if not hmac.compare_digest(signature_segment, expected_signature):
            raise JwtInvalidTokenError("令牌签名校验失败")

        now = int(time.time())
        exp = int(payload.get("exp", 0))
        nbf = int(payload.get("nbf", 0))

        if exp <= 0:
            raise JwtInvalidTokenError("令牌缺少过期时间")
        if now > exp:
            raise JwtExpiredTokenError("登录已过期，请重新登录")
        if now < nbf:
            raise JwtInvalidTokenError("令牌尚未生效")

        if payload.get("iss") != self._issuer:
            raise JwtInvalidTokenError("令牌发行方不匹配")
        if payload.get("aud") != self._audience:
            raise JwtInvalidTokenError("令牌受众不匹配")
        if payload.get("did") != self._device_id:
            raise JwtInvalidTokenError("令牌设备绑定校验失败")
        if payload.get("sub") != "admin":
            raise JwtInvalidTokenError("令牌用户不合法")

        return payload

    def _ensure_key_material(self) -> tuple[str, str]:
        config_map = self._config_manager.read_config_map()

        private_key = (config_map.get(self.PRIVATE_KEY_ENV, "") or "").strip()
        if not private_key:
            private_key = secrets.token_urlsafe(64)

        device_id = (config_map.get(self.DEVICE_ID_ENV, "") or "").strip()
        if not device_id:
            device_id = self._load_or_create_device_id_file()

        updates = []
        if config_map.get(self.PRIVATE_KEY_ENV, "").strip() != private_key:
            updates.append((self.PRIVATE_KEY_ENV, private_key))
        if config_map.get(self.DEVICE_ID_ENV, "").strip() != device_id:
            updates.append((self.DEVICE_ID_ENV, device_id))

        if updates:
            self._config_manager.apply_updates(
                updates=updates,
                sensitive_keys={self.PRIVATE_KEY_ENV},
                mask_token="******",
            )

        return private_key, device_id

    def _load_or_create_device_id_file(self) -> str:
        default_path = (Path(__file__).resolve().parents[2] / "data" / ".jwt_device_id").resolve()
        configured = (os.getenv(self.DEVICE_ID_FILE_ENV, "") or "").strip()
        file_path = Path(configured).expanduser().resolve() if configured else default_path

        if file_path.exists():
            existing = file_path.read_text(encoding="utf-8").strip()
            if existing:
                return existing

        seed = f"{uuid.getnode()}|{os.uname().nodename}|{secrets.token_hex(8)}"
        device_id = hashlib.sha256(seed.encode("utf-8")).hexdigest()

        if not file_path.parent.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(device_id + "\n", encoding="utf-8")

        return device_id

    def _load_expire_minutes(self) -> int:
        raw = (os.getenv(self.EXPIRES_MINUTES_ENV, "") or "").strip()
        if not raw:
            return self.DEFAULT_EXPIRES_MINUTES

        try:
            minutes = int(raw)
        except ValueError:
            return self.DEFAULT_EXPIRES_MINUTES

        return max(5, min(minutes, 24 * 60 * 7))

    def _sign(self, signing_input: bytes) -> str:
        signing_key = hmac.new(
            key=self._private_key.encode("utf-8"),
            msg=self._device_id.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature = hmac.new(signing_key, signing_input, hashlib.sha512).digest()
        return self._b64url_encode(signature)

    def _encode_token(self, payload: Dict[str, Any]) -> str:
        header = {
            "alg": self.ALGORITHM,
            "typ": "JWT",
        }
        header_segment = self._b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        payload_segment = self._b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
        signature_segment = self._sign(signing_input)
        return f"{header_segment}.{payload_segment}.{signature_segment}"

    @staticmethod
    def _decode_segment(segment: str) -> Dict[str, Any]:
        try:
            decoded = JwtAuthService._b64url_decode(segment)
            parsed = json.loads(decoded.decode("utf-8"))
            if not isinstance(parsed, dict):
                raise ValueError("decoded segment must be json object")
            return parsed
        except Exception as exc:
            raise JwtInvalidTokenError("令牌解析失败") from exc

    @staticmethod
    def _b64url_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    @staticmethod
    def _b64url_decode(data: str) -> bytes:
        padding = "=" * ((4 - len(data) % 4) % 4)
        return base64.urlsafe_b64decode(data + padding)
