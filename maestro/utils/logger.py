from typing import Any
from uuid import uuid4

from flask import request
from structlog.stdlib import BoundLogger, get_logger


class LoggerProxy:
    """Proxy that automatically uses request-bound logger when available."""

    def __getattr__(self, name: str) -> Any:
        return getattr(_get_maestro_logger(), name)


log: BoundLogger = LoggerProxy()  # type:ignore[assignment]


def _get_maestro_logger() -> BoundLogger:
    try:
        if hasattr(request, "logger"):
            return request.logger  # type:ignore[no-any-return]

        request.id = str(uuid4())[:8]  # type:ignore[attr-defined]
        request.logger = get_logger().bind(request_id=request.id)  # type:ignore[attr-defined]
        return request.logger  # type:ignore[attr-defined, no-any-return]

    except RuntimeError:
        return get_logger().bind(request_id=None)
