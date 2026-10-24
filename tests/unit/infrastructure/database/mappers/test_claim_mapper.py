"""
Unit tests for ClaimMapper.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from ai_news_digest.domain.enums.claim_status import ClaimStatus
from ai_news_digest.domain.enums.claim_type import ClaimType
from ai_news_digest.domain.models.claim import Claim
from ai_news_digest.infrastructure.database.mappers.claim_mapper import ClaimMapper
from ai_news_digest.infrastructure.database.models.claim_model import ClaimModel


@pytest.fixture
def sample_claim() -> Claim:
    """Create a sample Claim domain object."""
    return Claim(
        id=uuid4(),
        article_id=uuid4(),
        source_id=uuid4(),
        claim_text="The AI model launched on Monday.",
        claim_type=ClaimType.EVENT,
        confidence=0.88,
        status=ClaimStatus.SUPPORTED,
        evidence_support_score=0.92,
        schema_version="v1",
        prompt_version="prompt-v2",
        ai_provider="openai",
        ai_model="gpt-4o",
        processing_metadata={"extractor": "claim-v1", "tokens": "142"},
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_claim_model() -> ClaimModel:
    """Create a sample ClaimModel ORM entity."""
    return ClaimModel(
        id=str(uuid4()),
        article_id=str(uuid4()),
        source_id=str(uuid4()),
        claim_text="The AI model launched on Monday.",
        claim_type=ClaimType.EVENT.value,
        confidence=0.88,
        status=ClaimStatus.SUPPORTED.value,
        evidence_support_score=0.92,
        schema_version="v1",
        prompt_version="prompt-v2",
        ai_provider="openai",
        ai_model="gpt-4o",
        processing_metadata='{"extractor": "claim-v1", "tokens": "142"}',
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def test_claim_mapper_to_model(sample_claim: Claim) -> None:
    model = ClaimMapper.to_model(sample_claim)

    assert isinstance(model, ClaimModel)
    assert model.id == str(sample_claim.id)
    assert model.article_id == str(sample_claim.article_id)
    assert model.source_id == str(sample_claim.source_id)
    assert model.claim_text == sample_claim.claim_text
    assert model.claim_type == sample_claim.claim_type.value
    assert model.confidence == sample_claim.confidence
    assert model.status == sample_claim.status.value
    assert model.evidence_support_score == sample_claim.evidence_support_score
    assert model.schema_version == sample_claim.schema_version
    assert model.prompt_version == sample_claim.prompt_version
    assert model.ai_provider == sample_claim.ai_provider
    assert model.ai_model == sample_claim.ai_model


def test_claim_mapper_to_domain(sample_claim_model: ClaimModel) -> None:
    claim = ClaimMapper.to_domain(sample_claim_model)

    assert isinstance(claim, Claim)
    assert claim.id == UUID(sample_claim_model.id)
    assert claim.article_id == UUID(sample_claim_model.article_id)
    assert claim.source_id == UUID(sample_claim_model.source_id)
    assert claim.claim_text == sample_claim_model.claim_text
    assert claim.claim_type == ClaimType(sample_claim_model.claim_type)
    assert claim.confidence == sample_claim_model.confidence
    assert claim.status == ClaimStatus(sample_claim_model.status)
    assert claim.evidence_support_score == sample_claim_model.evidence_support_score
    assert claim.schema_version == sample_claim_model.schema_version
    assert claim.prompt_version == sample_claim_model.prompt_version
    assert claim.ai_provider == sample_claim_model.ai_provider
    assert claim.ai_model == sample_claim_model.ai_model
    assert claim.created_at == sample_claim_model.created_at


def test_claim_mapper_update_model(sample_claim: Claim, sample_claim_model: ClaimModel) -> None:
    sample_claim.claim_text = "Updated claim text."
    sample_claim.confidence = 0.5
    sample_claim.status = ClaimStatus.UNSUPPORTED
    sample_claim.evidence_support_score = 0.1
    sample_claim.ai_model = "gpt-3.5-turbo"

    ClaimMapper.update_model(sample_claim_model, sample_claim)

    assert sample_claim_model.claim_text == sample_claim.claim_text
    assert sample_claim_model.confidence == sample_claim.confidence
    assert sample_claim_model.status == sample_claim.status.value
    assert sample_claim_model.evidence_support_score == sample_claim.evidence_support_score
    assert sample_claim_model.ai_model == sample_claim.ai_model
    assert sample_claim_model.claim_type == sample_claim.claim_type.value


def test_claim_mapper_round_trip(sample_claim: Claim) -> None:
    model = ClaimMapper.to_model(sample_claim)
    restored = ClaimMapper.to_domain(model)

    assert restored.id == sample_claim.id
    assert restored.article_id == sample_claim.article_id
    assert restored.source_id == sample_claim.source_id
    assert restored.claim_text == sample_claim.claim_text
    assert restored.claim_type == sample_claim.claim_type
    assert restored.confidence == sample_claim.confidence
    assert restored.status == sample_claim.status
    assert restored.evidence_support_score == sample_claim.evidence_support_score
    assert restored.schema_version == sample_claim.schema_version
    assert restored.prompt_version == sample_claim.prompt_version
    assert restored.ai_provider == sample_claim.ai_provider
    assert restored.ai_model == sample_claim.ai_model
    assert restored.processing_metadata == sample_claim.processing_metadata


def test_claim_mapper_to_model_with_none_metadata(sample_claim: Claim) -> None:
    sample_claim.processing_metadata = None
    model = ClaimMapper.to_model(sample_claim)
    assert model.processing_metadata is None


def test_claim_mapper_to_domain_with_none_metadata() -> None:
    model = ClaimModel(
        id=str(uuid4()),
        article_id=str(uuid4()),
        source_id=str(uuid4()),
        claim_text="text",
        claim_type=ClaimType.OTHER.value,
        confidence=None,
        status=ClaimStatus.UNVERIFIED.value,
        evidence_support_score=None,
        schema_version="v1",
        prompt_version=None,
        ai_provider=None,
        ai_model=None,
        processing_metadata=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    claim = ClaimMapper.to_domain(model)
    assert claim.processing_metadata == {}


def test_claim_mapper_to_domain_invalid_claim_type_falls_back() -> None:
    model = ClaimModel(
        id=str(uuid4()),
        article_id=str(uuid4()),
        source_id=str(uuid4()),
        claim_text="text",
        claim_type="not_a_claim_type",
        confidence=None,
        status=ClaimStatus.UNVERIFIED.value,
        evidence_support_score=None,
        schema_version="v1",
        prompt_version=None,
        ai_provider=None,
        ai_model=None,
        processing_metadata=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    claim = ClaimMapper.to_domain(model)
    assert claim.claim_type == ClaimType.OTHER


def test_claim_mapper_to_domain_invalid_claim_status_falls_back() -> None:
    model = ClaimModel(
        id=str(uuid4()),
        article_id=str(uuid4()),
        source_id=str(uuid4()),
        claim_text="text",
        claim_type=ClaimType.OTHER.value,
        confidence=None,
        status="not_a_claim_status",
        evidence_support_score=None,
        schema_version="v1",
        prompt_version=None,
        ai_provider=None,
        ai_model=None,
        processing_metadata=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    claim = ClaimMapper.to_domain(model)
    assert claim.status == ClaimStatus.UNVERIFIED


def test_claim_mapper_to_domain_malformed_metadata_falls_back() -> None:
    model = ClaimModel(
        id=str(uuid4()),
        article_id=str(uuid4()),
        source_id=str(uuid4()),
        claim_text="text",
        claim_type=ClaimType.OTHER.value,
        confidence=None,
        status=ClaimStatus.UNVERIFIED.value,
        evidence_support_score=None,
        schema_version="v1",
        prompt_version=None,
        ai_provider=None,
        ai_model=None,
        processing_metadata="{not valid json",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    claim = ClaimMapper.to_domain(model)
    assert claim.processing_metadata == {}


def test_claim_mapper_to_domain_non_dict_metadata_falls_back() -> None:
    model = ClaimModel(
        id=str(uuid4()),
        article_id=str(uuid4()),
        source_id=str(uuid4()),
        claim_text="text",
        claim_type=ClaimType.OTHER.value,
        confidence=None,
        status=ClaimStatus.UNVERIFIED.value,
        evidence_support_score=None,
        schema_version="v1",
        prompt_version=None,
        ai_provider=None,
        ai_model=None,
        processing_metadata="[1, 2, 3]",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    claim = ClaimMapper.to_domain(model)
    assert claim.processing_metadata == {}


def test_claim_mapper_update_model_with_none_metadata(
    sample_claim: Claim, sample_claim_model: ClaimModel
) -> None:
    sample_claim.processing_metadata = None

    ClaimMapper.update_model(sample_claim_model, sample_claim)

    assert sample_claim_model.processing_metadata is None


def test_claim_mapper_update_model_with_empty_metadata(
    sample_claim: Claim, sample_claim_model: ClaimModel
) -> None:
    sample_claim.processing_metadata = {}

    ClaimMapper.update_model(sample_claim_model, sample_claim)

    assert sample_claim_model.processing_metadata is None
