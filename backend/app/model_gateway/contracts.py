from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


class ModelGateway(Protocol):
    async def generate_structured(
        self,
        *,
        messages: list[dict[str, str]],
        schema: type[StructuredModel],
        schema_name: str,
    ) -> StructuredModel: ...

    async def invoke_with_tools(
        self,
        *,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]: ...
