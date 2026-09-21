from enum import StrEnum


class ProviderErrorCategory(StrEnum):
    AUTH_FAILED = "AUTH_FAILED"
    RATE_LIMITED = "RATE_LIMITED"
    INVALID_REQUEST = "INVALID_REQUEST"
    TIMEOUT = "TIMEOUT"
    PROVIDER_DOWN = "PROVIDER_DOWN"
    INVALID_RESPONSE = "INVALID_RESPONSE"


class ProviderException(RuntimeError):
    def __init__(self, category: ProviderErrorCategory, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.category = category
        self.retryable = retryable
