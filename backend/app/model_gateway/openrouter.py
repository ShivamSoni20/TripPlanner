import json
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from app.model_gateway.errors import (
    ModelAuthenticationError,
    ModelGatewayError,
    ModelRateLimitError,
    ModelResponseError,
    StructuredOutputValidationError,
)

StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


class _Message(BaseModel):
    model_config = ConfigDict(extra="ignore")

    content: str | dict[str, Any] | None = None


class _Choice(BaseModel):
    message: _Message


class _ChatCompletion(BaseModel):
    choices: list[_Choice]
    usage: dict[str, int] | None = None


class OpenRouterModelGateway:
    endpoint = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float = 20,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is required for live model extraction")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._client = client

    async def generate_structured(
        self,
        *,
        messages: list[dict[str, str]],
        schema: type[StructuredModel],
        schema_name: str,
    ) -> StructuredModel:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "provider": {"require_parameters": True},
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema.model_json_schema(),
                },
            },
        }
        response = await self._post(payload)
        try:
            envelope = _ChatCompletion.model_validate(response.json())
            content = envelope.choices[0].message.content
        except (ValidationError, IndexError, ValueError) as error:
            raise ModelResponseError("OpenRouter returned an invalid response envelope") from error

        raw_output = json.dumps(content) if isinstance(content, dict) else content
        if not raw_output:
            raise ModelResponseError("OpenRouter returned an empty structured response")
        try:
            return schema.model_validate_json(raw_output)
        except ValidationError as error:
            raise StructuredOutputValidationError(
                "OpenRouter structured output failed validation",
                raw_output=raw_output,
                errors=error.errors(include_url=False),
            ) from error

    async def invoke_with_tools(
        self,
        *,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        response = await self._post(
            {"model": self.model, "messages": messages, "tools": tools, "temperature": 0}
        )
        data = response.json()
        if not isinstance(data, dict):
            raise ModelResponseError("OpenRouter returned an invalid tool response")
        return data

    async def _post(self, payload: dict[str, Any]) -> httpx.Response:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ShivamSoni20/TripPlanner",
            "X-Title": "TripPilot",
        }
        try:
            if self._client is not None:
                response = await self._client.post(self.endpoint, headers=headers, json=payload)
            else:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(self.endpoint, headers=headers, json=payload)
        except httpx.TimeoutException as error:
            raise ModelGatewayError("OpenRouter request timed out") from error
        except httpx.HTTPError as error:
            raise ModelGatewayError("OpenRouter request failed") from error

        if response.status_code in {401, 403}:
            raise ModelAuthenticationError("OpenRouter authentication failed")
        if response.status_code == 429:
            raise ModelRateLimitError("OpenRouter rate limit reached")
        if response.is_error:
            raise ModelGatewayError(f"OpenRouter request failed with status {response.status_code}")
        return response
