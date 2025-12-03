from contextlib import suppress
from contextvars import ContextVar
from typing import Any
from uuid import uuid4

from flask import request
from structlog.stdlib import BoundLogger, get_logger

_process_id_ctx: ContextVar[str | None] = ContextVar("process_id", default=None)


class LoggerProxy:
    """Proxy that automatically uses request-bound logger when available."""

    def __getattr__(self, name: str) -> Any:
        return getattr(_get_maestro_logger(), name)


log: BoundLogger = LoggerProxy()  # type:ignore[assignment]


def build_process_id(prefix: str) -> str:
    id = str(uuid4())[:8]
    return f"{prefix}-{id}"


def get_process_id() -> str | None:
    """Get the current request ID from Flask request or context variable."""
    with suppress(RuntimeError):
        if hasattr(request, "id"):
            return request.id  # type:ignore[no-any-return]

    return _process_id_ctx.get()


def set_process_id(process_id: str) -> None:
    """Set request ID in context variable for use in background threads."""
    _process_id_ctx.set(process_id)


def _get_maestro_logger() -> BoundLogger:
    try:
        if hasattr(request, "logger"):
            return request.logger  # type:ignore[no-any-return]

        request.id = build_process_id("webhook")  # type:ignore[attr-defined]
        request.logger = get_logger().bind(process_id=request.id)  # type:ignore[attr-defined]
        return request.logger  # type:ignore[attr-defined, no-any-return]

    except RuntimeError:
        process_id = _process_id_ctx.get()
        return get_logger().bind(process_id=process_id)
