import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Seo } from "../../components/Seo";
import { publicApi } from "../../api";
import { Badge } from "../../components/ui/Badge";
import { Spinner } from "../../components/ui/Spinner";
import { ErrorState } from "../../components/ui/ErrorState";
import { formatDateTime } from "../../utils";

export function ArticleDetailPage() {
  const { id } = useParams<{ id: string }>();

  const { data: article, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["article", id],
    queryFn: () => publicApi.article(id!),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="container-page py-16">
        <Spinner label="Loading article" />
      </div>
    );
  }

  if (isError || !article) {
    return (
      <div className="container-page py-16">
        <ErrorState
          message={error?.message ?? "Article not found."}
          retry={isError ? () => void refetch() : undefined}
        />
      </div>
    );
  }

  return (
    <>
      <Seo
        title={article.title}
        description={article.summary ?? undefined}
        ogType="article"
        canonical={`/news/${article.id}`}
        jsonLd={
          {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            headline: article.title,
            description: article.summary ?? undefined,
            datePublished: article.published_at ?? undefined,
            url: article.url,
            publisher: {
              "@type": "Organization",
              name: article.source_name ?? "AI News Digest",
            },
          } as Record<string, unknown>
        }
      />
      <article className="container-page py-8">
        <Link
          to="/news"
          className="text-sm font-medium text-brand-600 hover:underline"
        >
          &larr; Back to news
        </Link>
        <header className="mt-4 max-w-3xl">
          <div className="flex flex-wrap items-center gap-2">
            {article.source_name && (
              <Badge tone="brand">{article.source_name}</Badge>
            )}
            {article.category_name && <Badge>{article.category_name}</Badge>}
          </div>
          <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
            {article.title}
          </h1>
          <p className="mt-3 text-sm text-slate-500">
            {article.source_name && (
              <>
                Source: {article.source_name} &middot;{" "}
              </>
            )}
            Published {formatDateTime(article.published_at)}
          </p>
        </header>

        {article.summary && (
          <div className="mt-8 max-w-3xl rounded-xl bg-brand-50 p-6">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-brand-700">
              AI Summary
            </h2>
            <p className="mt-2 text-slate-800 leading-relaxed">{article.summary}</p>
          </div>
        )}

        {(article.key_takeaways && article.key_takeaways.length > 0) && (
          <div className="mt-8 max-w-3xl">
            <h2 className="text-lg font-semibold text-slate-900">Key Takeaways</h2>
            <ul className="mt-3 list-inside list-disc space-y-1 text-slate-700">
              {article.key_takeaways.map((takeaway, i) => (
                <li key={i}>{takeaway}</li>
              ))}
            </ul>
          </div>
        )}

        {article.why_it_matters && (
          <div className="mt-8 max-w-3xl">
            <h2 className="text-lg font-semibold text-slate-900">Why It Matters</h2>
            <p className="mt-2 text-slate-700 leading-relaxed">{article.why_it_matters}</p>
          </div>
        )}

        {article.companies && article.companies.length > 0 && (
          <div className="mt-8 max-w-3xl">
            <h2 className="text-lg font-semibold text-slate-900">Companies</h2>
            <div className="mt-3 flex flex-wrap gap-2">
              {article.companies.map((company) => (
                <Badge key={company}>{company}</Badge>
              ))}
            </div>
          </div>
        )}

        {article.topics && article.topics.length > 0 && (
          <div className="mt-8 max-w-3xl">
            <h2 className="text-lg font-semibold text-slate-900">Topics</h2>
            <div className="mt-3 flex flex-wrap gap-2">
              {article.topics.map((topic) => (
                <Badge key={topic} tone="success">{topic}</Badge>
              ))}
            </div>
          </div>
        )}

        {(article.importance_score != null || article.confidence != null) && (
          <div className="mt-8 max-w-3xl">
            <h2 className="text-lg font-semibold text-slate-900">Intelligence Metrics</h2>
            <div className="mt-3 flex flex-wrap gap-4 text-sm text-slate-600">
              {article.importance_score != null && (
                <span>Importance Score: {article.importance_score.toFixed(2)}</span>
              )}
              {article.confidence != null && (
                <span>Confidence: {article.confidence.toFixed(2)}</span>
              )}
            </div>
          </div>
        )}

        <div className="mt-8 max-w-3xl">
          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-brand-700"
          >
            Read the original article
            <span className="sr-only"> {article.title}</span>
          </a>
        </div>
      </article>
    </>
  );
}
