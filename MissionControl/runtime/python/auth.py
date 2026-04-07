"""
Minimal JWT (HS256) + PBKDF2-SHA256 password hashing using Python stdlib only.
No external dependencies required.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Optional


# ─── Base64URL helpers ────────────────────────────────────────────────────────

def _b64url_enc(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_dec(s: str) -> bytes:
    pad = 4 - len(s) % 4
    if pad != 4:
        s += "=" * pad
    return base64.urlsafe_b64decode(s)


# ─── JWT (HS256) ──────────────────────────────────────────────────────────────

_HEADER_B64 = _b64url_enc(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())


def _sign(header_b64: str, body_b64: str, secret: str) -> str:
    sig_input = f"{header_b64}.{body_b64}".encode("ascii")
    raw_sig = hmac.new(secret.encode("utf-8"), sig_input, hashlib.sha256).digest()
    return _b64url_enc(raw_sig)


def create_jwt(payload: dict, secret: str, expiry_seconds: int = 86400) -> str:
    """Create a signed HS256 JWT."""
    now = int(time.time())
    claims = {**payload, "iat": now, "exp": now + expiry_seconds}
    body_b64 = _b64url_enc(json.dumps(claims, separators=(",", ":")).encode("utf-8"))
    sig = _sign(_HEADER_B64, body_b64, secret)
    return f"{_HEADER_B64}.{body_b64}.{sig}"


def verify_jwt(token: str, secret: str) -> Optional[dict]:
    """Return decoded payload dict, or None if invalid / expired."""
    try:
        parts = token.strip().split(".")
        if len(parts) != 3:
            return None
        header_b64, body_b64, sig = parts
        expected_sig = _sign(header_b64, body_b64, secret)
        if not hmac.compare_digest(sig, expected_sig):
            return None
        claims = json.loads(_b64url_dec(body_b64))
        if claims.get("exp", 0) < time.time():
            return None
        return claims
    except Exception:
        return None


# ─── Password hashing (PBKDF2-SHA256, 260 000 iterations) ────────────────────

_PBKDF2_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    """Return '<hex-salt>:<hex-dk>' suitable for storage."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"{salt.hex()}:{dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Constant-time password verification against a stored PBKDF2 hash."""
    try:
        salt_hex, dk_hex = stored_hash.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        expected_dk = bytes.fromhex(dk_hex)
        candidate_dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
        return hmac.compare_digest(candidate_dk, expected_dk)
    except Exception:
        return False


def verify_password_plain(submitted: str, stored_plain: str) -> bool:
    """Constant-time comparison for plain-text passwords (env-var workflow)."""
    try:
        return hmac.compare_digest(submitted.encode("utf-8"), stored_plain.encode("utf-8"))
    except Exception:
        return False
