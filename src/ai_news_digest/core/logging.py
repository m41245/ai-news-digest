import logging
import logging.config
import sys
from typing import Any, cast

import structlog
from structlog.stdlib import BoundLogger

from ai_news_digest.core.config import settings


def configure_logging() -> None:
    """
    Configure application logging.

    Uses the standard logging module together with structlog
    to produce structured, production-friendly logs.
    """

    timestamper = structlog.processors.TimeStamper(fmt="iso")

    renderer: Any
    if settings.environment == "production":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processor": renderer,
                    "foreign_pre_chain": [
                        structlog.stdlib.add_log_level,
                        timestamper,
                    ],
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "stream": sys.stdout,
                    "formatter": "default",
                }
            },
            "root": {
                "handlers": ["default"],
                "level": settings.log_level,
            },
        }
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> BoundLogger:
    """
    Return a structured logger.
    """
    return cast(BoundLogger, structlog.get_logger(name))
