import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Seo } from "../../components/Seo";
import { publicApi } from "../../api";
import { Spinner } from "../../components/ui/Spinner";
import { ErrorState } from "../../components/ui/ErrorState";
import { Badge } from "../../components/ui/Badge";
import { formatDateTime } from "../../utils";

export function StoryClusterPage() {
  const { slug } = useParams<{ slug: string }>();

  const { data: cluster, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["storyCluster", slug],
    queryFn: () => publicApi.storyCluster(slug!),
    enabled: !!slug,
  });

  if (isLoading) {
    return (
      <div className="container-page py-16">
        <Spinner label="Loading story" />
      </div>
    );
  }

  if (isError || !cluster) {
    return (
      <div className="container-page py-16">
        <ErrorState
          message={error?.message ?? "Story not found."}
          retry={isError ? () => void refetch() : undefined}
        />
      </div>
    );
  }

  return (
    <>
      <Seo
        title={cluster.title}
        description={cluster.summary ?? undefined}
        ogType="article"
        canonical={`/stories/${cluster.slug}`}
      />
      <article className="container-page py-8">
        <Link
          to="/digests"
          className="text-sm font-medium text-brand-600 hover:underline"
        >
          &larr; Back to digests
        </Link>
        <header className="mt-4 max-w-3xl">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="brand">{cluster.status}</Badge>
            {cluster.importance_score != null && (
              <span className="text-sm text-slate-500">
                Importance: {cluster.importance_score.toFixed(2)}
              </span>
            )}
            {cluster.confidence != null && (
              <span className="text-sm text-slate-500">
                Confidence: {cluster.confidence.toFixed(2)}
              </span>
            )}
          </div>
          <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
            {cluster.title}
          </h1>
          <p className="mt-3 text-sm text-slate-500">
            {cluster.article_count} articles &middot; {cluster.source_count} sources &middot;{" "}
            Updated {formatDateTime(cluster.last_updated_at)}
          </p>
        </header>

        {cluster.summary && (
          <div className="mt-8 max-w-3xl rounded-xl bg-brand-50 p-6">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-brand-700">
              Summary
            </h2>
            <p className="mt-2 text-slate-800 leading-relaxed">{cluster.summary}</p>
          </div>
        )}

        {cluster.what_changed && cluster.what_changed.length > 0 && (
          <div className="mt-8 max-w-3xl">
            <h2 className="text-lg font-semibold text-slate-900">What Changed</h2>
            <ul className="mt-3 list-inside list-disc space-y-1 text-slate-700">
              {cluster.what_changed.map((change, i) => (
                <li key={i}>{change}</li>
              ))}
            </ul>
          </div>
        )}

        {cluster.contradictions && cluster.contradictions.length > 0 && (
          <div className="mt-8 max-w-3xl">
            <h2 className="text-lg font-semibold text-slate-900">Contradictions</h2>
            <div className="mt-3 space-y-2">
              {cluster.contradictions.map((c, i) => (
                <div key={i} className="rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-sm text-yellow-800">
                  {JSON.stringify(c)}
                </div>
              ))}
            </div>
          </div>
        )}

        {cluster.needs_verification && (
          <div className="mt-8 max-w-3xl">
            <div className="rounded-lg border border-orange-200 bg-orange-50 p-4 text-sm text-orange-800">
              This story may need verification due to detected contradictions.
            </div>
          </div>
        )}

        <div className="mt-8 max-w-3xl">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Recent Articles</h2>
          <div className="flex flex-col gap-4">
            {cluster.recent_articles.map((article) => (
              <div
                key={article.id}
                className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
              >
                <div className="flex flex-wrap items-center gap-2">
                  {article.source_name && (
                    <Badge tone="brand">{article.source_name}</Badge>
                  )}
                  {article.source_role && <Badge>{article.source_role}</Badge>}
                  <span className="ml-auto text-xs text-slate-500">
                    {formatDateTime(article.published_at)}
                  </span>
                </div>
                <h3 className="mt-2 text-lg font-semibold text-slate-900">
                  <a
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-brand-700 focus-visible:text-brand-700"
                  >
                    {article.title}
                  </a>
                </h3>
                {article.summary && (
                  <p className="mt-1 text-sm text-slate-600">{article.summary}</p>
                )}
                <div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-500">
                  {article.importance_score != null && (
                    <span>Importance: {article.importance_score.toFixed(2)}</span>
                  )}
                  {article.confidence != null && (
                    <span>Confidence: {article.confidence.toFixed(2)}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </article>
    </>
  );
}
