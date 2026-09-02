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
            {article.fetched_at && (
              <> &middot; Fetched {formatDateTime(article.fetched_at)}</>
            )}
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

        {article.content && (
          <div className="mt-8 max-w-3xl">
            <h2 className="text-lg font-semibold text-slate-900">Full article</h2>
            <div className="prose-body mt-3 whitespace-pre-wrap text-base">
              {article.content}
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
