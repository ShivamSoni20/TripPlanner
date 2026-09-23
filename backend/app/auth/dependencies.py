import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel
from supabase import Client, create_client

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class AuthenticatedUser(BaseModel):
    id: UUID
    email: str | None = None


def get_token_from_header(authorization: Annotated[str | None, Header()] = None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail={"category": "UNAUTHORIZED", "message": "Missing Authorization header"},
        )
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail={"category": "UNAUTHORIZED", "message": "Invalid Authorization header format"},
        )
    return parts[1]


def get_current_user(
    token: Annotated[str, Depends(get_token_from_header)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedUser:
    if settings.app_env == "test" and token.startswith("test-token-"):
        user_id_str = token.replace("test-token-", "")
        try:
            return AuthenticatedUser(id=UUID(user_id_str), email="test@example.com")
        except ValueError:
            pass

    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise HTTPException(
            status_code=503,
            detail={
                "category": "CONFIGURATION_ERROR",
                "message": "Supabase credentials are not configured",
            },
        )

    try:
        client: Client = create_client(settings.supabase_url, settings.supabase_publishable_key)
        user_response = client.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=401,
                detail={"category": "UNAUTHORIZED", "message": "Invalid or expired token"},
            )
        return AuthenticatedUser(
            id=UUID(user_response.user.id),
            email=user_response.user.email,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("JWT verification failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=401,
            detail={"category": "UNAUTHORIZED", "message": "Invalid or expired token"},
        ) from exc


def get_user_db_client(
    token: Annotated[str, Depends(get_token_from_header)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Client | None:
    if (
        settings.app_env == "test"
        or (settings.app_env == "test" and token.startswith("test-token-"))
        or not settings.supabase_url
        or not settings.supabase_publishable_key
    ):
        return None

    client: Client = create_client(settings.supabase_url, settings.supabase_publishable_key)
    client.postgrest.auth(token)
    return client
