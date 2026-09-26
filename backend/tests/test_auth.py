from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.auth.dependencies import get_current_user, get_token_from_header, get_user_db_client
from app.core.config import Settings


def test_missing_and_malformed_bearer_headers() -> None:
    for header in (None, "", "Token abc", "Bearer", "Bearer a b"):
        with pytest.raises(HTTPException) as error:
            get_token_from_header(header)
        assert error.value.status_code == 401


def test_synthetic_tokens_only_work_in_explicit_test_mode() -> None:
    token = "test-token-00000000-0000-0000-0000-000000000001"
    principal = get_current_user(token, Settings(app_env="test"))
    assert principal.id == UUID("00000000-0000-0000-0000-000000000001")
    with pytest.raises(HTTPException) as error:
        get_current_user(
            token, Settings(app_env="production", supabase_url=None, supabase_publishable_key=None)
        )
    assert error.value.status_code == 503


def test_verified_supabase_user_and_request_scoped_postgrest(monkeypatch) -> None:
    clients = []

    class FakeClient:
        def __init__(self) -> None:
            self.tokens = []
            self.auth = SimpleNamespace(
                get_user=lambda token: SimpleNamespace(
                    user=SimpleNamespace(
                        id="00000000-0000-0000-0000-000000000002", email="a@test.dev"
                    )
                    if token == "valid-token"
                    else None
                )
            )
            self.postgrest = SimpleNamespace(auth=self.tokens.append)

    def fake_create_client(url, key):
        assert url == "https://example.supabase.co"
        assert key == "publishable"
        client = FakeClient()
        clients.append(client)
        return client

    monkeypatch.setattr("app.auth.dependencies.create_client", fake_create_client)
    settings = Settings(
        app_env="production",
        supabase_url="https://example.supabase.co",
        supabase_publishable_key="publishable",
    )
    user = get_current_user("valid-token", settings)
    assert user.id == UUID("00000000-0000-0000-0000-000000000002")
    first = get_user_db_client("valid-token", settings)
    second = get_user_db_client("other-token", settings)
    assert first is not second
    assert first.tokens == ["valid-token"]
    assert second.tokens == ["other-token"]

    with pytest.raises(HTTPException) as error:
        get_current_user("invalid-token", settings)
    assert error.value.status_code == 401
    assert "invalid-token" not in str(error.value.detail)
