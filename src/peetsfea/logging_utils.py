from __future__ import annotations

import functools
import logging
import sys
import time
from typing import Any, Callable, ParamSpec, TypeVar

import structlog

P = ParamSpec("P")
R = TypeVar("R")

_CONFIGURED = False


def _configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )
    _CONFIGURED = True


def get_logger() -> structlog.stdlib.BoundLogger:
    _configure_logging()
    return structlog.get_logger("peetsfea")


def log_action(
    event: str,
    context_fn: Callable[P, dict[str, Any]] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            logger = get_logger()
            context: dict[str, Any] = {}
            if context_fn is not None:
                try:
                    context = context_fn(*args, **kwargs) or {}
                except Exception as exc:  # pragma: no cover
                    context = {"context_error": str(exc)}

            start = time.perf_counter()
            logger.info(f"{event}_start", action="start", **context)
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                duration_ms = int((time.perf_counter() - start) * 1000)
                logger.error(
                    f"{event}_error",
                    action="error",
                    duration_ms=duration_ms,
                    error=str(exc),
                    **context,
                )
                raise
            duration_ms = int((time.perf_counter() - start) * 1000)
            logger.info(f"{event}_end", action="end", duration_ms=duration_ms, **context)
            return result

        return wrapper

    return decorator
