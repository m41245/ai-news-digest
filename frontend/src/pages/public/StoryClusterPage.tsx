import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Seo } from "../../components/Seo";
import { publicApi } from "../../api";
import { ErrorState } from "../../components/ui/ErrorState";
import { Badge } from "../../components/ui/Badge";
import { EmptyState } from "../../components/ui/EmptyState";
import { Skeleton, StoryCardSkeleton } from "../../components/ui/Skeleton";
import { formatDateTime } from "../../utils";
import type { Conflict, StoryEvent } from "../../types";

export function StoryClusterPage() {
  const { slug } = useParams<{ slug: string }>();

  const { data: cluster, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["storyCluster", slug],
    queryFn: () => publicApi.storyCluster(slug!),
    enabled: !!slug,
  });

  const { data: timeline } = useQuery({
    queryKey: ["storyTimeline", cluster?.id],
    queryFn: () => publicApi.storyTimeline(cluster!.id),
    enabled: !!cluster?.id,
  });

  if (isLoading) {
    return (
      <div className="container-page py-8">
        <div className="max-w-3xl">
          <Skeleton className="h-4 w-24 mb-4" />
          <div className="flex flex-wrap items-center gap-2 mb-3">
            <Skeleton className="h-6 w-24" />
            <Skeleton className="h-5 w-20" />
            <Skeleton className="h-5 w-20" />
          </div>
          <Skeleton className="h-8 w-3/4 mb-3" />
          <Skeleton className="h-4 w-48 mb-8" />
          <div className="mb-8">
            <Skeleton className="h-5 w-24 mb-2" />
            <Skeleton className="h-4 w-full mb-2" />
            <Skeleton className="h-4 w-5/6" />
          </div>
          <div className="mb-8">
            <Skeleton className="h-6 w-32 mb-4" />
            <div className="flex flex-col gap-4">
              <StoryCardSkeleton />
              <StoryCardSkeleton />
              <StoryCardSkeleton />
            </div>
          </div>
        </div>
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
        description={cluster.summary ?? `A story cluster with ${cluster.article_count} articles from ${cluster.source_count} sources.`}
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
            {cluster.activity_status && (
              <Badge tone={cluster.activity_status === "breaking" ? "danger" : cluster.activity_status === "developing" ? "warning" : "neutral"}>
                {cluster.activity_status}
              </Badge>
            )}
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
            <h2 className="text-lg font-semibold text-slate-900">Conflicting Reports</h2>
            <p className="mt-1 text-sm text-slate-500">
              Different sources report incompatible facts about this story.
              This does not mean any source is wrong.
            </p>
            <div className="mt-3 space-y-4">
              {cluster.contradictions.map((c, i) => (
                <div
                  key={i}
                  className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
                >
                  {typeof c === "string" ? c : JSON.stringify(c)}
                </div>
              ))}
            </div>
          </div>
        )}

        {cluster.conflicts && cluster.conflicts.length > 0 && (
          <div className="mt-8 max-w-3xl">
            <h2 className="text-lg font-semibold text-slate-900">Conflicting Reports</h2>
            <p className="mt-1 text-sm text-slate-500">
              Different sources report incompatible facts about this story.
              This does not mean any source is wrong.
            </p>
            <div className="mt-3 space-y-4">
              {(cluster.conflicts as Conflict[]).map((c, i) => (
                <div
                  key={i}
                  className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">{c.explanation}</span>
                    <span className="text-xs text-amber-700">
                      {c.conflict_type}
                      {c.confidence != null && ` · ${(c.confidence * 100).toFixed(0)}%`}
                    </span>
                  </div>
                  <div className="mt-2 grid gap-2 text-xs text-amber-800">
                    {c.source_a_name && (
                      <div>
                        <span className="font-medium">{c.source_a_name}:</span>{" "}
                        {c.published_at_a && (
                          <span className="text-amber-600">
                            [{new Date(c.published_at_a).toLocaleDateString()}]
                          </span>
                        )}
                      </div>
                    )}
                    {c.source_b_name && (
                      <div>
                        <span className="font-medium">{c.source_b_name}:</span>{" "}
                        {c.published_at_b && (
                          <span className="text-amber-600">
                            [{new Date(c.published_at_b).toLocaleDateString()}]
                          </span>
                        )}
                      </div>
                    )}
                  </div>
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

        {timeline && timeline.events.length > 0 && (
          <div className="mt-8 max-w-3xl">
            <h2 className="text-lg font-semibold text-slate-900">Story Evolution</h2>
            <div className="mt-4 space-y-4">
              {timeline.events.map((event: StoryEvent) => (
                <div
                  key={event.id}
                  className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone="brand">{event.event_type}</Badge>
                    <span className="text-xs text-slate-500">
                      {event.event_time ? formatDateTime(event.event_time) : "Unknown date"}
                    </span>
                    <span className="text-xs text-slate-500">
                      Confidence: {(event.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                  <h3 className="mt-2 text-base font-semibold text-slate-900">
                    {event.title}
                  </h3>
                  {event.description && (
                    <p className="mt-1 text-sm text-slate-600">{event.description}</p>
                  )}
                  <div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-500">
                    <span>{event.article_count} articles</span>
                    <span>{event.claim_count} claims</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {(cluster.related_companies.length > 0 || cluster.related_topics.length > 0) && (
          <div className="mt-8 max-w-3xl">
            <h2 className="text-lg font-semibold text-slate-900">Knowledge Connections</h2>
            <p className="mt-1 text-sm text-slate-500">
              Entities connected to this story based on extracted relationships.
            </p>
            {cluster.related_companies.length > 0 && (
              <div className="mt-3">
                <h3 className="text-sm font-medium text-slate-700">Companies</h3>
                <div className="mt-2 flex flex-wrap gap-2">
                  {cluster.related_companies.map((name: string) => (
                    <span
                      key={name}
                      className="rounded-full bg-brand-50 px-3 py-1 text-sm text-brand-800"
                    >
                      {name}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {cluster.related_topics.length > 0 && (
              <div className="mt-4">
                <h3 className="text-sm font-medium text-slate-700">Topics</h3>
                <div className="mt-2 flex flex-wrap gap-2">
                  {cluster.related_topics.map((name: string) => (
                    <span
                      key={name}
                      className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-800"
                    >
                      {name}
                    </span>
                  ))}
                </div>
              </div>
            )}
            <p className="mt-2 text-xs text-slate-500">
              {cluster.relationship_count} relationship{cluster.relationship_count === 1 ? "" : "s"} found
            </p>
          </div>
        )}

        <div className="mt-8 max-w-3xl">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Recent Articles</h2>
          {cluster.recent_articles.length > 0 ? (
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
          ) : (
            <EmptyState
              title="No articles"
              description="There are no articles linked to this story yet."
            />
          )}
        </div>
      </article>
    </>
  );
}
