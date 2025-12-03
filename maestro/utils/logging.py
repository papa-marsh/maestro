from contextlib import suppress
from contextvars import ContextVar
from typing import Any
from uuid import uuid4

from flask import request
from structlog.stdlib import BoundLogger, get_logger

_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


class LoggerProxy:
    """Proxy that automatically uses request-bound logger when available."""

    def __getattr__(self, name: str) -> Any:
        return getattr(_get_maestro_logger(), name)


log: BoundLogger = LoggerProxy()  # type:ignore[assignment]


def get_request_id() -> str | None:
    """Get the current request ID from Flask request or context variable."""
    with suppress(RuntimeError):
        if hasattr(request, "id"):
            return request.id  # type:ignore[no-any-return]

    return _request_id_ctx.get()


def set_request_id(request_id: str) -> None:
    """Set request ID in context variable for use in background threads."""
    _request_id_ctx.set(request_id)


def _get_maestro_logger() -> BoundLogger:
    try:
        if hasattr(request, "logger"):
            return request.logger  # type:ignore[no-any-return]

        request.id = str(uuid4())[:8]  # type:ignore[attr-defined]
        request.logger = get_logger().bind(request_id=request.id)  # type:ignore[attr-defined]
        return request.logger  # type:ignore[attr-defined, no-any-return]

    except RuntimeError:
        request_id = _request_id_ctx.get()
        return get_logger().bind(request_id=request_id)
