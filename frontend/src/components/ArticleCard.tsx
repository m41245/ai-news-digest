import { Link } from "react-router-dom";
import type { Article } from "../types";
import { Card } from "./ui/Card";
import { Badge } from "./ui/Badge";
import { formatDate, truncate } from "../utils";

interface ArticleCardProps {
  article: Article;
}

export function ArticleCard({ article }: ArticleCardProps) {
  return (
    <Card as="article" className="transition-shadow hover:shadow-md">
      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2">
          {article.source_name && (
            <Badge tone="brand">{article.source_name}</Badge>
          )}
          {article.category_name && <Badge>{article.category_name}</Badge>}
          <span className="ml-auto text-xs text-slate-500">
            {formatDate(article.published_at)}
          </span>
        </div>
        <h2 className="text-lg font-semibold text-slate-900">
          <Link
            to={`/news/${article.id}`}
            className="hover:text-brand-700 focus-visible:text-brand-700"
          >
            {article.title}
          </Link>
        </h2>
        {article.summary && (
          <p className="prose-body text-sm">{truncate(article.summary, 200)}</p>
        )}
        <div className="mt-1 flex items-center gap-3">
          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-medium text-brand-600 hover:underline"
          >
            Read original
            <span className="sr-only"> for {article.title}</span>
          </a>
        </div>
      </div>
    </Card>
  );
}
