import logging
import logging.config
import re
import sys
from collections.abc import Mapping, MutableMapping
from typing import Any, cast

import structlog
from structlog.stdlib import BoundLogger

from ai_news_digest.core.config import settings

_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "passwd",
        "pwd",
        "api_key",
        "apikey",
        "secret",
        "token",
        "authorization",
        "jwt",
        "bearer",
        "redis_password",
        "db_password",
        "database_password",
        "smtp_password",
        "cookie",
        "sessionid",
        "csrftoken",
        "access_token",
        "refresh_token",
    }
)


_SENSITIVE_REGEXES = [
    re.compile(r"(?i)(password|passwd|pwd)\s*[=:]\s*\S+"),
    re.compile(r"(?i)(api[_-]?key|apikey)\s*[=:]\s*\S+"),
    re.compile(r"(?i)(secret|token)\s*[=:]\s*\S+"),
    re.compile(r"(?i)(authorization)\s*[=:]\s*\S+"),
    re.compile(
        r"(?i)(redis[_-]?password|db[_-]?password|database[_-]?password|smtp[_-]?password)\s*[=:]\s*\S+"
    ),
    re.compile(r"(?i)(cookie)\s*[=:]\s*\S+"),
    re.compile(r"\beyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+(?:\.[A-Za-z0-9-_]+)?\b"),
    re.compile(r"\b[A-Za-z0-9+\/]{40,}={0,2}\b"),
]


def _redact_match(m: re.Match[str]) -> str:
    text = m.group(0)
    for sep in ("=", ":", " "):
        if sep in text:
            return text.split(sep, 1)[0] + sep + "***REDACTED***"
    return "***REDACTED***"


def _redact_string(value: str) -> str:
    for pattern in _SENSITIVE_REGEXES:
        value = pattern.sub(_redact_match, value)
    return value


def redact_sensitive_data(
    logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
) -> Mapping[str, Any]:
    for key in list(event_dict.keys()):
        if key.lower() in _SENSITIVE_KEYS:
            event_dict[key] = "***REDACTED***"
        elif isinstance(event_dict[key], str):
            event_dict[key] = _redact_string(event_dict[key])
    event = event_dict.get("event")
    if isinstance(event, str):
        event_dict["event"] = _redact_string(event)
    return event_dict


def add_service_and_environment(
    logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
) -> Mapping[str, Any]:
    event_dict.setdefault("service", "ai-news-digest")
    event_dict.setdefault("environment", settings.environment)
    return event_dict


def configure_logging() -> None:
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
            add_service_and_environment,
            structlog.stdlib.add_log_level,
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            redact_sensitive_data,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> BoundLogger:
    return cast(BoundLogger, structlog.get_logger(name))
