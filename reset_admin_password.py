# -*- coding: utf-8 -*-
"""Reset admin password from trusted server shell."""

from __future__ import annotations

import argparse
import getpass
import sys

from src.services.auth_service import AuthService


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset admin password from server shell.")
    parser.add_argument("--username", default="admin", help="Admin username (default: admin)")
    parser.add_argument("--password", default="", help="New password (avoid passing in shell history)")
    args = parser.parse_args()

    username = (args.username or "admin").strip() or "admin"
    password = args.password

    if not password:
        first = getpass.getpass("Enter new admin password: ")
        second = getpass.getpass("Confirm new admin password: ")
    else:
        first = password
        second = password

    service = AuthService()
    try:
        result = service.reset_password_from_server(
            username=username,
            new_password=first,
            confirm_password=second,
        )
    except Exception as exc:  # pragma: no cover
        print(f"[ERROR] {exc}")
        return 1

    print(f"[OK] {result['message']} (username={result['username']})")
    print("[INFO] Password hash has been updated in .env")
    return 0


if __name__ == "__main__":
    sys.exit(main())
