"""
Unit tests for M69 GenerateIntelligentDigestUseCase.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from ai_news_digest.application.ai.editorial_schemas import (
    EditorialDigestOutput,
    EditorialTopStory,
)
from ai_news_digest.application.services.digest_editorial_generator import (
    DigestEditorialResult,
)
from ai_news_digest.application.use_cases.digest.generate_intelligent_digest import (
    GenerateIntelligentDigestUseCase,
    get_settings_digest_format,
)
from ai_news_digest.core.config import Settings
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.digest import Digest
from ai_news_digest.domain.models.source import Source
from ai_news_digest.domain.models.story_cluster import StoryCluster


def _make_cluster(
    cluster_id: str,
    title: str,
    summary: str = "",
    score: float = 0.5,
) -> StoryCluster:
    return StoryCluster(
        id=uuid4(),
        title=title,
        slug=f"test-{cluster_id}",
        summary=summary,
        first_published_at=datetime.now(UTC),
        last_updated_at=datetime.now(UTC),
        ranking_score=score,
        representative_article_id=uuid4(),
    )


def _make_article(title: str, cluster_id: uuid4, source_id: uuid4 | None = None) -> Article:
    article = Article.create(
        title=title,
        url=f"https://example.com/{uuid4()}",
        summary=f"Summary for {title}",
        content=None,
        source_id=source_id or uuid4(),
        published_at=datetime.now(UTC),
    )
    object.__setattr__(article, "cluster_id", cluster_id)
    return article


def _make_source() -> Source:
    return Source(
        id=uuid4(),
        name="Test Source",
        feed_url="https://example.com/feed",
        website_url=None,
        description=None,
        is_active=True,
        source_type="other",
        status="verified",
        created_at=datetime.now(UTC),
    )


def _make_mock_container(
    clusters: list[StoryCluster],
    cluster_articles: dict,
    existing_digest: Digest = None,
    editorial_result: DigestEditorialResult = None,
):
    container = MagicMock()

    async def mock_get_by_title(title):
        return existing_digest

    async def mock_find_recent_active_clusters(cutoff, limit):
        return clusters

    async def mock_list_all():
        return [_make_source()]

    async def mock_list_by_cluster_id(cluster_id):
        return cluster_articles.get(str(cluster_id), [])

    async def mock_create(digest):
        return digest

    async def mock_commit():
        pass

    container.digest_repository = MagicMock()
    container.digest_repository.get_by_title = mock_get_by_title
    container.digest_repository.create = mock_create
    container.digest_repository.commit = mock_commit

    container.story_cluster_repository = MagicMock()
    container.story_cluster_repository.find_recent_active_clusters = (
        mock_find_recent_active_clusters
    )

    container.source_repository = MagicMock()
    container.source_repository.list_all = mock_list_all

    container.article_repository = MagicMock()
    container.article_repository.list_by_cluster_id = mock_list_by_cluster_id

    if editorial_result is None:
        top_story = None
        if clusters:
            top_story = EditorialTopStory(
                cluster_id=str(clusters[0].id),
                headline="Top Story",
                summary="Summary",
                key_takeaways=("K1",),
                why_it_matters="Important",
            )
        editorial_result = DigestEditorialResult(
            editorial_output=EditorialDigestOutput(
                title="Test Digest",
                introduction="Test intro",
                top_story=top_story,
                stories=(),
            ),
            generation_method="ai",
            provider="openai",
            model="gpt-4o-mini",
            prompt_version="v1",
            fallback_used=False,
        )

    container.generate_intelligent_digest = MagicMock()
    container.generate_intelligent_digest.execute = AsyncMock(return_value=editorial_result)

    return container


class TestGenerateIntelligentDigestUseCase:
    """Tests for the M69 intelligent digest generation use case."""

    async def test_existing_digest_reused_when_not_forced(self):
        """When a digest for today already exists and force=False, reuse it."""
        existing = Digest.create(
            title="AI News Digest - 2024-01-01",
            content="Existing content",
            digest_format=get_settings_digest_format(),
        )
        container = _make_mock_container(
            clusters=[],
            cluster_articles={},
            existing_digest=existing,
        )

        use_case = GenerateIntelligentDigestUseCase(
            story_cluster_repository=container.story_cluster_repository,
            digest_repository=container.digest_repository,
            source_repository=container.source_repository,
            article_repository=container.article_repository,
            editorial_generator=MagicMock(),
        )

        result = await use_case.execute(force=False)
        assert result.generation_method == "unknown"
        assert result.fallback_used is False

    async def test_no_clusters_returns_fallback(self):
        """When no eligible clusters exist, return a fallback digest."""
        container = _make_mock_container(
            clusters=[],
            cluster_articles={},
            existing_digest=None,
        )

        use_case = GenerateIntelligentDigestUseCase(
            story_cluster_repository=container.story_cluster_repository,
            digest_repository=container.digest_repository,
            source_repository=container.source_repository,
            article_repository=container.article_repository,
            editorial_generator=MagicMock(),
        )

        result = await use_case.execute(force=True)
        assert result.generation_method == "fallback"
        assert result.fallback_used is True
        assert result.error == "no_eligible_clusters"

    async def test_editorial_disabled_returns_fallback(self):
        """When editorial is disabled, return fallback digest."""
        cluster = _make_cluster("c1", "Cluster 1", "Summary", score=0.9)
        article = _make_article("Article 1", cluster.id)

        container = _make_mock_container(
            clusters=[cluster],
            cluster_articles={str(cluster.id): [article]},
            existing_digest=None,
        )

        use_case = GenerateIntelligentDigestUseCase(
            story_cluster_repository=container.story_cluster_repository,
            digest_repository=container.digest_repository,
            source_repository=container.source_repository,
            article_repository=container.article_repository,
            editorial_generator=MagicMock(),
        )

        disabled_settings = Settings(digest_editorial_enabled=False)
        patch_path = (
            "ai_news_digest.application.use_cases.digest"
            ".generate_intelligent_digest.get_settings"
        )
        with patch(patch_path, return_value=disabled_settings):
            result = await use_case.execute(force=True)
        assert result.generation_method == "fallback"
        assert result.fallback_used is True

    async def test_ai_path_persists_digest(self):
        """Successful AI generation persists the digest."""
        cluster = _make_cluster("c1", "Cluster 1", "Summary", score=0.9)
        article = _make_article("Article 1", cluster.id)

        container = _make_mock_container(
            clusters=[cluster],
            cluster_articles={str(cluster.id): [article]},
            existing_digest=None,
        )

        async def mock_generate(*args, **kwargs):
            return DigestEditorialResult(
                editorial_output=EditorialDigestOutput(
                    title="Test Digest",
                    introduction="Test intro",
                    top_story=EditorialTopStory(
                        cluster_id=str(cluster.id),
                        headline="Top Story",
                        summary="Summary",
                        key_takeaways=("K1",),
                        why_it_matters="Important",
                    ),
                    stories=(),
                ),
                generation_method="ai",
                provider="openai",
                model="gpt-4o-mini",
                prompt_version="v1",
                fallback_used=False,
            )

        editorial_generator = MagicMock()
        editorial_generator.generate = mock_generate

        use_case = GenerateIntelligentDigestUseCase(
            story_cluster_repository=container.story_cluster_repository,
            digest_repository=container.digest_repository,
            source_repository=container.source_repository,
            article_repository=container.article_repository,
            editorial_generator=editorial_generator,
        )

        result = await use_case.execute(force=True)
        assert result.generation_method == "ai"
        assert result.fallback_used is False


class TestCollectArticleIds:
    """Tests for _collect_article_ids type correctness."""

    async def test_collects_uuids_not_strings(self):
        """_collect_article_ids must return UUID objects, not strings."""
        cluster = _make_cluster("c1", "Cluster 1")
        article = _make_article("Article 1", cluster.id)

        container = _make_mock_container(
            clusters=[cluster],
            cluster_articles={str(cluster.id): [article]},
            existing_digest=None,
        )

        use_case = GenerateIntelligentDigestUseCase(
            story_cluster_repository=container.story_cluster_repository,
            digest_repository=container.digest_repository,
            source_repository=container.source_repository,
            article_repository=container.article_repository,
            editorial_generator=MagicMock(),
        )

        ids = use_case._collect_article_ids([(cluster, [article])])
        assert len(ids) == 1
        assert isinstance(ids[0], uuid4().__class__)


class TestRankClusters:
    """Tests for _rank_clusters deterministic ordering."""

    async def test_ranking_sorts_by_score_descending(self):
        """Clusters are sorted by ranking_score descending, then by id."""
        c1 = _make_cluster("c1", "Cluster 1", score=0.9)
        c2 = _make_cluster("c2", "Cluster 2", score=0.5)
        c3 = _make_cluster("c3", "Cluster 3", score=0.7)

        container = _make_mock_container(
            clusters=[c1, c2, c3],
            cluster_articles={},
            existing_digest=None,
        )

        use_case = GenerateIntelligentDigestUseCase(
            story_cluster_repository=container.story_cluster_repository,
            digest_repository=container.digest_repository,
            source_repository=container.source_repository,
            article_repository=container.article_repository,
            editorial_generator=MagicMock(),
        )

        ranked = await use_case._rank_clusters([c1, c2, c3])
        assert len(ranked) == 3
        assert ranked[0][0].id == c1.id
        assert ranked[1][0].id == c3.id
        assert ranked[2][0].id == c2.id

    async def test_top_story_is_highest_ranked(self):
        """Top story is the highest-ranked cluster."""
        c1 = _make_cluster("c1", "Cluster 1", score=0.9)
        c2 = _make_cluster("c2", "Cluster 2", score=0.5)

        container = _make_mock_container(
            clusters=[c1, c2],
            cluster_articles={},
            existing_digest=None,
        )

        use_case = GenerateIntelligentDigestUseCase(
            story_cluster_repository=container.story_cluster_repository,
            digest_repository=container.digest_repository,
            source_repository=container.source_repository,
            article_repository=container.article_repository,
            editorial_generator=MagicMock(),
        )

        ranked = await use_case._rank_clusters([c1, c2])
        top_id = await use_case._get_top_story_cluster_id(ranked)
        assert top_id == c1.id
