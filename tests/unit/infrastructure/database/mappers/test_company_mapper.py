"""
Unit tests for CompanyMapper.
"""

from __future__ import annotations

from ai_news_digest.domain.models.company import Company
from ai_news_digest.infrastructure.database.mappers.company_mapper import (
    CompanyMapper,
    _slugify,
)
from ai_news_digest.infrastructure.database.models.company_model import CompanyModel


def test_company_mapper_round_trip() -> None:
    company = Company.create(name="Acme", slug="acme-corp")

    model = CompanyMapper.to_model(company)

    assert isinstance(model, CompanyModel)
    assert model.id == str(company.id)
    assert model.name == company.name
    assert model.slug == company.slug

    restored = CompanyMapper.to_domain(model)

    assert restored.id == company.id
    assert restored.name == company.name
    assert restored.slug == company.slug
    assert restored.created_at == company.created_at


def test_company_mapper_update_model() -> None:
    company = Company.create(name="Acme", slug="acme")
    model = CompanyModel(
        id=str(company.id),
        name="Old",
        slug="old",
        created_at=company.created_at,
        updated_at=company.created_at,
    )

    CompanyMapper.update_model(model, company)

    assert model.name == "Acme"
    assert model.slug == "acme"


def test_company_mapper_does_not_clear_slug_when_company_slug_is_none() -> None:
    company = Company.create(name="Acme", slug=None)
    model = CompanyModel(
        id=str(company.id),
        name="Old",
        slug="existing",
        created_at=company.created_at,
        updated_at=company.created_at,
    )

    CompanyMapper.update_model(model, company)

    assert model.name == "Acme"
    assert model.slug == "existing"


def test_company_mapper_slug_lookup_normalization() -> None:
    assert _slugify("Acme Corp.") == "acme-corp"
    assert _slugify("A" * 100) == "a" * 64


def test_company_mapper_slug_does_not_end_with_hyphen_after_truncation() -> None:
    value = "a" * 63 + " " + "b" * 10
    slug = _slugify(value)
    assert not slug.endswith("-")
    assert slug == "a" * 63
