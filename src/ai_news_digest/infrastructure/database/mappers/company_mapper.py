from __future__ import annotations

import re
import unicodedata
from uuid import UUID

from ai_news_digest.domain.models.company import Company
from ai_news_digest.infrastructure.database.models.company_model import CompanyModel


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    result = (slug or "company")[:64].rstrip("-")
    return result or "company"


class CompanyMapper:
    @staticmethod
    def to_model(company: Company) -> CompanyModel:
        slug = company.slug or _slugify(company.name)
        return CompanyModel(
            id=str(company.id),
            name=company.name,
            slug=slug,
            created_at=company.created_at,
            updated_at=company.created_at,
        )

    @staticmethod
    def to_domain(model: CompanyModel) -> Company:
        return Company(
            id=UUID(model.id),
            name=model.name,
            created_at=model.created_at,
            slug=getattr(model, "slug", None),
            article_count=getattr(model, "article_count", 0) or 0,
        )

    @staticmethod
    def update_model(model: CompanyModel, company: Company) -> None:
        model.name = company.name
        if company.slug:
            model.slug = company.slug
