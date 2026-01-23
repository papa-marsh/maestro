"""
Internal utility logic & helpers.
Not intended to be used by script modules
"""

import importlib
import logging
import os
import sys
from collections.abc import Mapping, MutableMapping
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from maestro import config
from maestro.utils.exceptions import MissingScriptsDirectoryError
from maestro.utils.logging import log


def test_mode_active() -> bool:
    return "pytest" in sys.modules


def shell_mode_active() -> bool:
    if os.environ.get("FLASK_RUN_FROM_CLI") == "true":
        return "shell" in sys.argv

    return hasattr(sys, "ps1") or bool(sys.flags.interactive)


def add_timezone_timestamp(
    _logger: Any,
    _method_name: str,
    event_dict: MutableMapping[str, Any],
) -> Mapping[str, Any]:
    """Add timestamp in configured timezone."""
    event_dict["timestamp"] = datetime.now(config.TIMEZONE).isoformat()
    return event_dict


def configure_logging() -> None:
    """Configure structlog with colored output for all environments."""
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            add_timezone_timestamp,
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(min_level=logging.DEBUG),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging to use structlog's output
    # This captures logs from libraries like APScheduler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer(colors=True),
        )
    )

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


def load_script_modules() -> None:
    """
    Auto-discover and import all Python modules in the scripts directory.
    This ensures that trigger decorators (eg. @state_change_trigger) and DB models get registered.
    """
    scripts_dir = Path("/code/scripts")
    if not scripts_dir.exists():
        scripts_dir = Path.cwd() / "scripts"
    if not scripts_dir.exists():
        raise MissingScriptsDirectoryError("Failed to find scripts directory while loading modules")

    scripts_path = str(scripts_dir)
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)
        log.info("Added scripts directory to Python path", path=scripts_path)

    python_files = list(scripts_dir.rglob("*.py"))
    loaded_count = 0
    error_count = 0

    for python_file in python_files:
        if python_file.name.startswith("_") or python_file.name.startswith("test"):
            continue

        relative_path = python_file.relative_to(scripts_dir)
        module_name = str(relative_path.with_suffix("")).replace("/", ".").replace("\\", ".")

        try:
            log.info("Loading scripts module", module=module_name)
            importlib.import_module(module_name)
            loaded_count += 1
        except Exception as e:
            log.exception("Failed to load scripts module", module=module_name, error=str(e))
            error_count += 1

    log.info("Script loading completed", loaded=loaded_count, errors=error_count)
