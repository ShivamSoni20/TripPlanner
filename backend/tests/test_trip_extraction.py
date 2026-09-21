import json
from datetime import date

import httpx
import pytest

from app.model_gateway.errors import StructuredOutputValidationError
from app.model_gateway.openrouter import OpenRouterModelGateway
from app.services.trip_extraction import ExtractedTripFields, ModelTripExtractor


def complete_fields() -> ExtractedTripFields:
    return ExtractedTripFields(
        origin="Indore",
        destination="Goa",
        start_date=date(2026, 11, 12),
        end_date=date(2026, 11, 17),
        travelers=2,
        budget_amount=30_000,
        budget_currency="INR",
        interests=["beaches", "history", "nightlife"],
        pace="relaxed",
        transport_preferences=[],
        accommodation_preferences=[],
    )


class RetryGateway:
    def __init__(self) -> None:
        self.calls = 0
        self.messages: list[list[dict[str, str]]] = []

    async def generate_structured(self, *, messages, schema, schema_name):
        _ = (schema, schema_name)
        self.calls += 1
        self.messages.append(messages.copy())
        if self.calls == 1:
            raise StructuredOutputValidationError(
                "invalid",
                raw_output='{"origin": 123}',
                errors=[{"loc": ["origin"], "msg": "Input should be a valid string"}],
            )
        return complete_fields()

    async def invoke_with_tools(self, *, messages, tools):
        _ = (messages, tools)
        return {}


@pytest.mark.asyncio
async def test_extractor_retries_validation_once() -> None:
    gateway = RetryGateway()
    result = await ModelTripExtractor(gateway, today=date(2026, 9, 22)).extract(
        "Indore to Goa from 12 to 17 November 2026 for two under ₹30,000"
    )

    assert result.status == "complete"
    assert result.constraints is not None
    assert result.constraints.destination == "Goa"
    assert gateway.calls == 2
    assert "Validation errors" in gateway.messages[1][-1]["content"]


class MissingFieldsGateway(RetryGateway):
    async def generate_structured(self, *, messages, schema, schema_name):
        _ = (messages, schema, schema_name)
        fields = complete_fields()
        return fields.model_copy(update={"origin": None, "start_date": None, "end_date": None})


@pytest.mark.asyncio
async def test_extractor_returns_missing_requirements_without_guessing() -> None:
    result = await ModelTripExtractor(MissingFieldsGateway()).extract("Plan a relaxed Goa trip")

    assert result.status == "needs_input"
    assert result.constraints is None
    assert result.missing == ["origin", "start_date", "end_date"]
    assert result.question is not None
    assert "origin" in result.question


@pytest.mark.asyncio
async def test_openrouter_uses_strict_json_schema_and_validates_response() -> None:
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": complete_fields().model_dump_json()}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        gateway = OpenRouterModelGateway(api_key="test-key", model="test/model", client=client)
        result = await gateway.generate_structured(
            messages=[{"role": "user", "content": "plan a trip"}],
            schema=ExtractedTripFields,
            schema_name="trip_constraints",
        )

    assert result.destination == "Goa"
    assert captured["response_format"]["type"] == "json_schema"
    assert captured["response_format"]["json_schema"]["strict"] is True
    assert captured["provider"]["require_parameters"] is True
