"""
Unit tests for M82 conflict candidate generation.
"""

from __future__ import annotations

import pytest
from uuid import UUID, uuid4

from ai_news_digest.application.evaluation.conflict_candidates import (
    ClaimContext,
    build_claim_contexts,
    generate_candidates,
)
from ai_news_digest.domain.enums.claim_type import ClaimType
from ai_news_digest.domain.models.claim import Claim


def _make_claim(
    claim_id: str | None = None,
    article_id: str | None = None,
    source_id: str | None = None,
    claim_text: str = "Test claim.",
    claim_type: ClaimType = ClaimType.FACT,
) -> Claim:
    return Claim.create(
        article_id=uuid4() if article_id is None else UUID(article_id),
        source_id=uuid4() if source_id is None else UUID(source_id),
        claim_text=claim_text,
        claim_type=claim_type,
    )


class TestBuildClaimContexts:
    def test_returns_empty_for_missing_article(self) -> None:
        claim = _make_claim()
        contexts = build_claim_contexts(
            claims=[claim],
            articles={},
            sources={},
            company_ids_by_article={},
            topic_ids_by_article={},
        )
        assert contexts == []

    def test_builds_context_for_valid_claim(self) -> None:
        from ai_news_digest.domain.models.article import Article
        from ai_news_digest.domain.models.source import Source

        article = Article.create(
            title="Test",
            url="https://example.com",
            summary="Test",
            content="Test",
            source_id=uuid4(),
            published_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        )
        source = Source.create(
            name="Test Source",
            feed_url="https://example.com/feed",
        )
        claim = _make_claim(article_id=str(article.id), source_id=str(source.id))
        contexts = build_claim_contexts(
            claims=[claim],
            articles={article.id: article},
            sources={source.id: source},
            company_ids_by_article={article.id: frozenset()},
            topic_ids_by_article={article.id: frozenset()},
        )
        assert len(contexts) == 1
        assert contexts[0].claim == claim
        assert contexts[0].article == article
        assert contexts[0].source == source


class TestGenerateCandidates:
    def test_no_candidates_without_overlap(self) -> None:
        from ai_news_digest.domain.models.article import Article
        from ai_news_digest.domain.models.source import Source

        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        article_a = Article.create(
            title="A", url="https://a.com", summary="A", content="A",
            source_id=uuid4(), published_at=now,
        )
        article_b = Article.create(
            title="B", url="https://b.com", summary="B", content="B",
            source_id=uuid4(), published_at=now,
        )
        source_a = Source.create(name="A", feed_url="https://a.com/feed")
        source_b = Source.create(name="B", feed_url="https://b.com/feed")
        claim_a = Claim.create(
            article_id=article_a.id, source_id=source_a.id,
            claim_text="OpenAI released GPT-5.", claim_type=ClaimType.ANNOUNCEMENT,
        )
        claim_b = Claim.create(
            article_id=article_b.id, source_id=source_b.id,
            claim_text="Google released Gemini 2.", claim_type=ClaimType.ANNOUNCEMENT,
        )
        ctx_a = ClaimContext(
            claim=claim_a, article=article_a, source=source_a,
            company_ids=frozenset(), topic_ids=frozenset(),
            normalized_tokens=frozenset({"openai", "gpt", "released"}),
            claim_type_group="event",
        )
        ctx_b = ClaimContext(
            claim=claim_b, article=article_b, source=source_b,
            company_ids=frozenset(), topic_ids=frozenset(),
            normalized_tokens=frozenset({"google", "gemini", "released"}),
            claim_type_group="event",
        )
        candidates = generate_candidates([ctx_a, ctx_b])
        assert candidates == []

    def test_generates_candidate_with_company_overlap(self) -> None:
        from ai_news_digest.domain.models.article import Article
        from ai_news_digest.domain.models.source import Source

        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        article_a = Article.create(
            title="A", url="https://a.com", summary="A", content="A",
            source_id=uuid4(), published_at=now,
        )
        article_b = Article.create(
            title="B", url="https://b.com", summary="B", content="B",
            source_id=uuid4(), published_at=now,
        )
        source_a = Source.create(name="A", feed_url="https://a.com/feed")
        source_b = Source.create(name="B", feed_url="https://b.com/feed")
        company_id = str(uuid4())
        claim_a = Claim.create(
            article_id=article_a.id, source_id=source_a.id,
            claim_text="OpenAI released GPT-5.", claim_type=ClaimType.ANNOUNCEMENT,
        )
        claim_b = Claim.create(
            article_id=article_b.id, source_id=source_b.id,
            claim_text="OpenAI announced GPT-6.", claim_type=ClaimType.ANNOUNCEMENT,
        )
        ctx_a = ClaimContext(
            claim=claim_a, article=article_a, source=source_a,
            company_ids=frozenset({company_id}), topic_ids=frozenset(),
            normalized_tokens=frozenset({"openai", "gpt", "released"}),
            claim_type_group="event",
        )
        ctx_b = ClaimContext(
            claim=claim_b, article=article_b, source=source_b,
            company_ids=frozenset({company_id}), topic_ids=frozenset(),
            normalized_tokens=frozenset({"openai", "gpt", "announced"}),
            claim_type_group="event",
        )
        candidates = generate_candidates([ctx_a, ctx_b])
        assert len(candidates) == 1
        assert candidates[0].same_source is False

    def test_skips_same_claim(self) -> None:
        from ai_news_digest.domain.models.article import Article
        from ai_news_digest.domain.models.source import Source

        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        article = Article.create(
            title="A", url="https://a.com", summary="A", content="A",
            source_id=uuid4(), published_at=now,
        )
        source = Source.create(name="A", feed_url="https://a.com/feed")
        company_id = str(uuid4())
        claim = Claim.create(
            article_id=article.id, source_id=source.id,
            claim_text="OpenAI released GPT-5.", claim_type=ClaimType.ANNOUNCEMENT,
        )
        ctx = ClaimContext(
            claim=claim, article=article, source=source,
            company_ids=frozenset({company_id}), topic_ids=frozenset(),
            normalized_tokens=frozenset({"openai", "gpt", "released"}),
            claim_type_group="event",
        )
        candidates = generate_candidates([ctx, ctx])
        assert candidates == []

    def test_respects_max_total_candidates(self) -> None:
        from ai_news_digest.domain.models.article import Article
        from ai_news_digest.domain.models.source import Source

        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        company_id = str(uuid4())
        contexts = []
        for _ in range(10):
            article = Article.create(
                title="A", url=f"https://{uuid4()}.com", summary="A", content="A",
                source_id=uuid4(), published_at=now,
            )
            source = Source.create(name="A", feed_url="https://a.com/feed")
            claim = Claim.create(
                article_id=article.id, source_id=source.id,
                claim_text="OpenAI released GPT-5.", claim_type=ClaimType.ANNOUNCEMENT,
            )
            contexts.append(ClaimContext(
                claim=claim, article=article, source=source,
                company_ids=frozenset({company_id}), topic_ids=frozenset(),
                normalized_tokens=frozenset({"openai", "gpt", "released"}),
                claim_type_group="event",
            ))
        candidates = generate_candidates(contexts, max_total_candidates=5)
        assert len(candidates) <= 5


__all__ = ["TestBuildClaimContexts", "TestGenerateCandidates"]
