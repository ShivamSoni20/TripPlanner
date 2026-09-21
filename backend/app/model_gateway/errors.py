from typing import Any


class ModelGatewayError(RuntimeError):
    """A safe, normalized model gateway failure."""


class ModelAuthenticationError(ModelGatewayError):
    pass


class ModelRateLimitError(ModelGatewayError):
    pass


class ModelResponseError(ModelGatewayError):
    pass


class StructuredOutputValidationError(ModelResponseError):
    def __init__(self, message: str, *, raw_output: str, errors: list[dict[str, Any]]) -> None:
        super().__init__(message)
        self.raw_output = raw_output
        self.errors = errors
