"""
Generate intelligent daily digest use case for M69.

Transforms ranked StoryClusters into a high-quality, structured daily AI news digest.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID
from zoneinfo import ZoneInfo

from ai_news_digest.application.ai.editorial_schemas import (
    EditorialDigestOutput,
    EditorialStory,
)
from ai_news_digest.application.services.digest_editorial_generator import (
    DigestEditorialGenerator,
    build_fallback_digest,
)
from ai_news_digest.core.config import get_settings
from ai_news_digest.domain.models.digest import Digest
from ai_news_digest.domain.models.source import Source
from ai_news_digest.domain.models.story_cluster import StoryCluster
from ai_news_digest.domain.ports.digest_repository import DigestRepository
from ai_news_digest.domain.ports.source_repository import SourceRepository
from ai_news_digest.domain.ports.story_cluster_repository import StoryClusterRepository

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DigestStoryCandidate:
    """A ranked story cluster with its articles for editorial generation."""

    cluster: StoryCluster
    articles: list[object]  # Article objects
    ranking_score: float | None = None


@dataclass(slots=True)
class IntelligentDigestResult:
    """Result returned after creating an intelligent digest."""

    digest_id: str
    generated_at: datetime
    candidate_count: int
    story_count: int
    top_story_cluster_id: str | None
    generation_method: str
    provider: str | None
    model: str | None
    fallback_used: bool
    error: str | None = None


class GenerateIntelligentDigestUseCase:
    """
    Create an intelligent daily digest from ranked StoryClusters.

    This is the M69 editorial layer. It:
    1. Determines the digest date/timezone
    2. Finds eligible ranked StoryClusters
    3. Selects bounded candidates deterministically
    4. Identifies the M68 Top Story
    5. Calls the LLM once for editorial generation
    6. Validates structured output
    7. Falls back to deterministic Markdown on failure
    8. Persists the digest
    """

    def __init__(
        self,
        story_cluster_repository: StoryClusterRepository,
        digest_repository: DigestRepository,
        source_repository: SourceRepository,
        article_repository: object,
        editorial_generator: DigestEditorialGenerator,
    ) -> None:
        self._story_cluster_repository = story_cluster_repository
        self._digest_repository = digest_repository
        self._source_repository = source_repository
        self._article_repository = article_repository
        self._editorial_generator = editorial_generator

    async def execute(
        self,
        *,
        title: str | None = None,
        limit: int | None = None,
        force: bool = False,
    ) -> IntelligentDigestResult:
        """
        Create an intelligent daily digest and persist it.

        If a digest for today already exists and force=False, returns the
        existing digest id.
        """
        settings = get_settings()
        effective_limit = limit if limit is not None else settings.digest_max_editorial_stories

        tz = ZoneInfo(settings.digest_timezone)
        now = datetime.now(UTC)
        today = now.astimezone(tz).date()
        digest_date = today.isoformat()

        if title is None:
            title = f"AI News Digest - {digest_date}"

        existing = await self._digest_repository.get_by_title(title)
        if existing is not None and not force:
            logger.info("Today's digest already exists, reusing", title=title)
            return IntelligentDigestResult(
                digest_id=str(existing.id),
                generated_at=existing.generated_at,
                candidate_count=0,
                story_count=len(existing.article_ids),
                top_story_cluster_id=existing.top_story_cluster_id,
                generation_method=existing.generation_method or "unknown",
                provider=existing.provider,
                model=existing.model,
                fallback_used=(existing.generation_method == "fallback"),
                error=None,
            )

        cutoff = now - self._ranking_lookback_timedelta()
        eligible_clusters = (
            await self._story_cluster_repository.find_recent_active_clusters(
                cutoff=cutoff,
                limit=settings.ranking_max_candidates,
            )
        )

        if not eligible_clusters:
            logger.info("No eligible story clusters for digest")
            content, stories_list, top_cluster_id = build_fallback_digest(
                digest_date=digest_date,
                candidate_stories=[],
                top_story_cluster_id=None,
                source_map={},
            )
            digest = Digest.create(
                title=title,
                content=content,
                digest_format=get_settings_digest_format(),
                top_story_cluster_id=top_cluster_id,
                stories=stories_list,
                generation_metadata={"candidate_count": 0, "fallback_reason": "no_clusters"},
                generation_method="fallback",
            )
            persisted = await self._digest_repository.create(digest)
            await self._digest_repository.commit()
            return IntelligentDigestResult(
                digest_id=str(persisted.id),
                generated_at=persisted.generated_at,
                candidate_count=0,
                story_count=0,
                top_story_cluster_id=str(top_cluster_id) if top_cluster_id else None,
                generation_method="fallback",
                provider=None,
                model=None,
                fallback_used=True,
                error="no_eligible_clusters",
            )

        ranked_candidates = await self._rank_clusters(eligible_clusters)
        top_story_cluster_id = await self._get_top_story_cluster_id(ranked_candidates)

        bounded = ranked_candidates[:effective_limit]
        if not bounded:
            content, stories_list, top_cluster_id = build_fallback_digest(
                digest_date=digest_date,
                candidate_stories=[],
                top_story_cluster_id=top_story_cluster_id,
                source_map={},
            )
            digest = Digest.create(
                title=title,
                content=content,
                digest_format=get_settings_digest_format(),
                top_story_cluster_id=top_cluster_id,
                stories=stories_list,
                generation_metadata={"candidate_count": 0, "fallback_reason": "empty_after_filter"},
                generation_method="fallback",
            )
            persisted = await self._digest_repository.create(digest)
            await self._digest_repository.commit()
            return IntelligentDigestResult(
                digest_id=str(persisted.id),
                generated_at=persisted.generated_at,
                candidate_count=len(eligible_clusters),
                story_count=0,
                top_story_cluster_id=str(top_cluster_id) if top_cluster_id else None,
                generation_method="fallback",
                provider=None,
                model=None,
                fallback_used=True,
                error="empty_after_filter",
            )

        source_map = await self._build_source_map()
        candidate_stories = await self._load_candidate_articles(bounded)

        if not settings.digest_editorial_enabled:
            content, stories_list, top_cluster_id = build_fallback_digest(
                digest_date=digest_date,
                candidate_stories=candidate_stories,
                top_story_cluster_id=top_story_cluster_id,
                source_map=source_map,
            )
            digest = Digest.create(
                title=title,
                content=content,
                digest_format=get_settings_digest_format(),
                article_ids=self._collect_article_ids(candidate_stories),
                top_story_cluster_id=top_cluster_id,
                stories=stories_list,
                generation_metadata={"candidate_count": len(candidate_stories)},
                generation_method="fallback",
            )
            persisted = await self._digest_repository.create(digest)
            await self._digest_repository.commit()
            return IntelligentDigestResult(
                digest_id=str(persisted.id),
                generated_at=persisted.generated_at,
                candidate_count=len(candidate_stories),
                story_count=len(stories_list),
                top_story_cluster_id=str(top_cluster_id) if top_cluster_id else None,
                generation_method="fallback",
                provider=None,
                model=None,
                fallback_used=True,
                error="editorial_disabled",
            )

        editorial_result = await self._editorial_generator.generate(
            digest_date=digest_date,
            candidate_stories=candidate_stories,
            top_story_cluster_id=top_story_cluster_id,
            source_map=source_map,
        )

        if editorial_result.editorial_output is None or editorial_result.fallback_used:
            logger.info(
                "Using fallback digest generation",
                error=editorial_result.error,
            )
            content, stories_list, top_cluster_id = build_fallback_digest(
                digest_date=digest_date,
                candidate_stories=candidate_stories,
                top_story_cluster_id=top_story_cluster_id,
                source_map=source_map,
            )
            generation_method = "fallback"
            provider = editorial_result.provider
            model = editorial_result.model
            error = editorial_result.error
            fallback_used = True
        else:
            content = self._render_editorial_output(
                editorial_result.editorial_output, candidate_stories, source_map
            )
            stories_list = self._serialize_stories(editorial_result.editorial_output)
            top_cluster_id = (
                UUID(editorial_result.editorial_output.top_story.cluster_id)
                if editorial_result.editorial_output.top_story
                else top_story_cluster_id
            )
            generation_method = "ai"
            provider = editorial_result.provider
            model = editorial_result.model
            error = None
            fallback_used = False

        generation_metadata = {
            "prompt_version": editorial_result.prompt_version,
            "candidate_count": len(candidate_stories),
            "story_count": len(stories_list),
            "error": error,
        }

        digest = Digest.create(
            title=title,
            content=content,
            digest_format=get_settings_digest_format(),
            article_ids=self._collect_article_ids(candidate_stories),
            top_story_cluster_id=top_cluster_id,
            stories=stories_list,
            generation_metadata=generation_metadata,
            generation_method=generation_method,
            provider=provider,
            model=model,
        )

        try:
            persisted = await self._digest_repository.create(digest)
            await self._digest_repository.commit()
        except Exception:
            await self._digest_repository.rollback()
            raise

        return IntelligentDigestResult(
            digest_id=str(persisted.id),
            generated_at=persisted.generated_at,
            candidate_count=len(candidate_stories),
            story_count=len(stories_list),
            top_story_cluster_id=str(top_cluster_id) if top_cluster_id else None,
            generation_method=generation_method,
            provider=provider,
            model=model,
            fallback_used=fallback_used,
            error=error,
        )

    async def _rank_clusters(
        self, clusters: list[StoryCluster]
    ) -> list[tuple[StoryCluster, float | None]]:
        """Sort clusters by ranking_score descending, deterministically."""
        ranked = [
            (c, c.ranking_score) for c in clusters if c.ranking_score is not None
        ]
        ranked.sort(key=lambda x: (-(x[1] or 0.0), str(x[0].id)))
        return ranked

    async def _get_top_story_cluster_id(
        self, ranked: list[tuple[StoryCluster, float | None]]
    ) -> UUID | None:
        """Get the top story cluster ID from ranked candidates."""
        if not ranked:
            return None
        return ranked[0][0].id

    async def _build_source_map(self) -> dict[UUID, Source]:
        """Build source_id -> Source map."""
        sources = await self._source_repository.list_all()
        return {s.id: s for s in sources}

    async def _load_candidate_articles(
        self, ranked: list[tuple[StoryCluster, float | None]]
    ) -> list[tuple[StoryCluster, list[object]]]:
        """Load articles for each candidate cluster."""
        result: list[tuple[StoryCluster, list[object]]] = []
        list_by_cluster = self._article_repository.list_by_cluster_id
        for cluster, _ in ranked:
            articles = await list_by_cluster(cluster.id)
            result.append((cluster, articles))
        return result

    def _collect_article_ids(
        self, candidate_stories: list[tuple[StoryCluster, list[object]]]
    ) -> list[str]:
        """Collect article IDs from candidate stories."""
        ids: list[str] = []
        for _, articles in candidate_stories:
            for article in articles:
                ids.append(str(article.id))
        return ids

    def _render_editorial_output(
        self,
        output: EditorialDigestOutput,
        candidate_stories: list[tuple[StoryCluster, list[object]]],
        source_map: dict[UUID, Source],
    ) -> str:
        """Render the editorial output to Markdown."""
        lines: list[str] = [
            f"# {output.title}",
            "",
            f"**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "---",
            "",
            output.introduction,
            "",
            "---",
            "",
        ]

        if output.top_story is not None:
            ts = output.top_story
            lines.append("## Top Story")
            lines.append("")
            lines.append(f"### {ts.headline}")
            lines.append("")
            lines.append(ts.summary)
            lines.append("")
            if ts.key_takeaways:
                lines.append("**Key Takeaways:**")
                lines.append("")
                for takeaway in ts.key_takeaways:
                    lines.append(f"- {takeaway}")
                lines.append("")
            if ts.why_it_matters:
                lines.append(f"**Why it matters:** {ts.why_it_matters}")
                lines.append("")
            cluster = next(
                (c for c, _ in candidate_stories if str(c.id) == ts.cluster_id),
                None,
            )
            if cluster:
                articles = [a for c, arts in candidate_stories if c.id == cluster.id for a in arts]
                rep = next(
                    (a for a in articles if str(a.id) == str(cluster.representative_article_id)),
                    articles[0] if articles else None,
                )
                if rep:
                    src = source_map.get(rep.source_id)
                    source_name = src.name if src else "Unknown Source"
                    lines.append(f"**Source:** {source_name}")
                    lines.append(f"[Read article]({rep.url})")
                    lines.append("")

        if output.stories:
            lines.append("## Stories")
            lines.append("")
            for story in output.stories:
                lines.append(f"### {story.headline}")
                lines.append("")
                lines.append(story.summary)
                lines.append("")
                if story.key_takeaways:
                    lines.append("**Key Takeaways:**")
                    lines.append("")
                    for takeaway in story.key_takeaways:
                        lines.append(f"- {takeaway}")
                    lines.append("")
                if story.why_it_matters:
                    lines.append(f"**Why it matters:** {story.why_it_matters}")
                    lines.append("")
                cluster = next(
                    (c for c, _ in candidate_stories if str(c.id) == story.cluster_id),
                    None,
                )
                if cluster:
                    articles = [
                        a for c, arts in candidate_stories
                        if c.id == cluster.id for a in arts
                    ]
                    rep = next(
                        (a for a in articles
                         if str(a.id) == str(cluster.representative_article_id)),
                        articles[0] if articles else None,
                    )
                    if rep:
                        src = source_map.get(rep.source_id)
                        source_name = src.name if src else "Unknown Source"
                        lines.append(f"**Source:** {source_name}")
                        lines.append(f"[Read article]({rep.url})")
                        lines.append("")

        return "\n".join(lines)

    def _serialize_stories(self, output: EditorialStory) -> list[dict]:
        """Serialize editorial stories to JSON-serializable dicts."""
        stories: list[dict] = []
        if output.top_story is not None:
            ts = output.top_story
            stories.append(
                {
                    "cluster_id": ts.cluster_id,
                    "headline": ts.headline,
                    "summary": ts.summary,
                    "key_takeaways": list(ts.key_takeaways),
                    "why_it_matters": ts.why_it_matters,
                }
            )
        for story in output.stories:
            stories.append(
                {
                    "cluster_id": story.cluster_id,
                    "headline": story.headline,
                    "summary": story.summary,
                    "key_takeaways": list(story.key_takeaways),
                    "why_it_matters": story.why_it_matters,
                }
            )
        return stories

    def _ranking_lookback_timedelta(self) -> timedelta:
        """Get the ranking lookback timedelta from settings."""
        from datetime import timedelta

        settings = get_settings()
        return timedelta(hours=settings.ranking_lookback_hours)


def get_settings_digest_format():
    """Get the default digest format from settings."""
    from ai_news_digest.domain.enums.digest_format import DigestFormat

    return DigestFormat.MARKDOWN


__all__ = [
    "DigestStoryCandidate",
    "GenerateIntelligentDigestUseCase",
    "IntelligentDigestResult",
]
