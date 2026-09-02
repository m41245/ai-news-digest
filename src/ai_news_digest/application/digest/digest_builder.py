from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from ai_news_digest.application.dto.digest_article_view import DigestArticleView


class DigestBuilder:
    """
    Builds deterministic Markdown digest content from selected articles.
    """

    def build(
        self,
        title: str,
        generated_at: datetime,
        articles: list[DigestArticleView],
    ) -> str:
        """
        Build Markdown content for a digest.

        Articles are grouped by category and ordered deterministically
        within each group.
        """
        lines: list[str] = [
            f"# {title}",
            "",
            f"**Generated:** {generated_at.astimezone(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "---",
            "",
        ]

        if not articles:
            lines.append("*No articles in this digest.*")
            return "\n".join(lines)

        by_category: dict[str, list[DigestArticleView]] = defaultdict(list)
        for article in articles:
            category = article.category_name or "Uncategorized"
            by_category[category].append(article)

        for category in sorted(by_category):
            lines.append(f"## {category}")
            lines.append("")

            category_articles = sorted(
                by_category[category],
                key=lambda article: (
                    article.published_at,
                    article.article_id,
                ),
                reverse=True,
            )

            for article in category_articles:
                lines.append(f"### {article.title}")
                lines.append("")
                lines.append(f"**Source:** {article.source_name}")
                lines.append(f"**Published:** {article.published_at.strftime('%Y-%m-%d')}")
                lines.append(f"**Category:** {category}")
                lines.append("")
                lines.append(article.summary)
                lines.append("")
                lines.append(f"[Read article]({article.url})")
                lines.append("")

        return "\n".join(lines)
