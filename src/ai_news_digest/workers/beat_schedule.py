from __future__ import annotations

from celery.schedules import crontab

from ai_news_digest.core.config import settings
from ai_news_digest.workers.celery_app import celery_app

# ======================================================================
# Celery Beat Schedule Configuration
# ======================================================================
#
# This schedule defines the automated pipeline for daily news digest generation.
#
# Pipeline Flow:
# 1. RSS Ingestion (06:00 UTC) - Fetch articles from all enabled sources
# 2. Article Summarization (06:30 UTC) - Summarize newly fetched articles
# 3. Article Categorization (07:00 UTC) - Categorize summarized articles
# 4. Digest Generation (08:00 UTC) - Generate daily digest from categorized articles
# 5. Email Delivery (08:30 UTC) - Send digest via email to subscribers
#
# ======================================================================

celery_app.conf.beat_schedule = {
    # RSS Ingestion - Run daily at 06:00 UTC
    "daily-rss-ingestion": {
        "task": "workers.tasks.ingest.fetch_all_sources",
        "schedule": crontab(
            hour=6,
            minute=0,
        ),
        "options": {
            "expires": 3600,  # Task expires after 1 hour
        },
    },
    # Article Summarization - Run daily at 06:30 UTC
    "daily-article-summarization": {
        "task": "workers.tasks.process.summarize_pending_articles",
        "schedule": crontab(
            hour=6,
            minute=30,
        ),
        "options": {
            "expires": 7200,  # Task expires after 2 hours
        },
    },
    # Article Categorization - Run daily at 07:00 UTC
    "daily-article-categorization": {
        "task": "workers.tasks.process.categorize_pending_articles",
        "schedule": crontab(
            hour=7,
            minute=0,
        ),
        "options": {
            "expires": 7200,  # Task expires after 2 hours
        },
    },
    # Digest Generation - Run daily at 08:00 UTC
    "daily-digest-generation": {
        "task": "workers.tasks.digest.generate_daily_digest",
        "schedule": crontab(
            hour=settings.digest_schedule_hour,
            minute=settings.digest_schedule_minute,
        ),
        "options": {
            "expires": 3600,  # Task expires after 1 hour
        },
    },
    # Email Delivery - Run daily at 08:30 UTC
    "daily-email-delivery": {
        "task": "workers.tasks.deliver.send_latest_digest",
        "schedule": crontab(
            hour=8,
            minute=30,
        ),
        "options": {
            "expires": 3600,  # Task expires after 1 hour
        },
    },
}

__all__ = ["celery_app"]
