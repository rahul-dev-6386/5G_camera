import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta


class TokenError(Exception):
    pass


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    password_salt = salt or secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        password_salt.encode("utf-8"),
        100_000,
    ).hex()
    return password_salt, password_hash


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    _, computed_hash = hash_password(password, salt)
    return hmac.compare_digest(computed_hash, expected_hash)


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_jwt_token(subject: str, secret_key: str, expires_delta: timedelta, token_type: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": int(datetime.now(UTC).timestamp()),
        "exp": int((datetime.now(UTC) + expires_delta).timestamp()),
        "jti": secrets.token_urlsafe(12),
    }
    header_segment = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_segment = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    signature = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_segment}.{payload_segment}.{_b64url_encode(signature)}"


def decode_jwt_token(token: str, secret_key: str, expected_type: str) -> dict:
    try:
        header_segment, payload_segment, signature_segment = token.split(".")
    except ValueError as exc:
        raise TokenError("Malformed token.") from exc

    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    expected_signature = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    actual_signature = _b64url_decode(signature_segment)
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise TokenError("Invalid token signature.")

    payload = json.loads(_b64url_decode(payload_segment))
    if payload.get("type") != expected_type:
        raise TokenError("Invalid token type.")

    if int(payload.get("exp", 0)) <= int(datetime.now(UTC).timestamp()):
        raise TokenError("Token has expired.")

    return payload
