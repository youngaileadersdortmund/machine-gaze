from hashlib import sha256
from hmac import compare_digest

from fastapi import Header, HTTPException, status

from .settings import get_settings


def hash_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def verify_token(token: str, token_hash: str) -> bool:
    return compare_digest(hash_token(token), token_hash)


def _extract_token(authorization: str | None, explicit_token: str | None) -> str | None:
    if explicit_token:
        return explicit_token
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


async def require_admin(
    authorization: str | None = Header(default=None),
    x_admin_token: str | None = Header(default=None),
) -> None:
    settings = get_settings()
    token = _extract_token(authorization, x_admin_token)
    if not token or not compare_digest(token, settings.admin_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin token required.",
        )


async def require_worker(
    authorization: str | None = Header(default=None),
    x_worker_token: str | None = Header(default=None),
) -> None:
    settings = get_settings()
    token = _extract_token(authorization, x_worker_token)
    if not token or not compare_digest(token, settings.worker_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Worker token required.",
        )
