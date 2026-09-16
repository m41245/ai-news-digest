import { useParams, Link } from "react-router-dom";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Seo } from "../../components/Seo";
import { publicApi } from "../../api";
import { intelligenceWorkspaceApi } from "../../api";
import { ErrorState } from "../../components/ui/ErrorState";
import { Badge } from "../../components/ui/Badge";
import { EmptyState } from "../../components/ui/EmptyState";
import { Skeleton } from "../../components/ui/Skeleton";
import { Button } from "../../components/ui/Button";
import { IntelligenceQualityPanel } from "../../components/IntelligenceQualityPanel";
import { ProvenanceBadge } from "../../components/ProvenanceBadge";
import { formatDateTime } from "../../utils";
import { useAuth } from "../../auth/AuthContext";
import type {
  BriefEntitiesContext,
  BriefEntityContext,
  BriefGraphConnection,
  BriefQualityIndicators,
  BriefRelatedStoryItem,
  BriefStoryEvolution,
  BriefTimelineItem,
  BriefTrendContext,
} from "../../types";

function BriefSkeleton() {
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
      </div>
    </div>
  );
}

export function StoryClusterPage() {
  const { slug } = useParams<{ slug: string }>();
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuth();
  const [saving, setSaving] = useState(false);
  const [following, setFollowing] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [isFollowed, setIsFollowed] = useState(false);

  const { data: brief, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["storyClusterBrief", slug],
    queryFn: () => publicApi.storyClusterBrief(slug!),
    enabled: !!slug,
  });

  const { data: savedList } = useQuery({
    queryKey: ["saved-stories"],
    queryFn: () => intelligenceWorkspaceApi.listSavedStories({ limit: 100 }),
    enabled: isAuthenticated,
  });

  const { data: followedList } = useQuery({
    queryKey: ["followed-stories"],
    queryFn: () => intelligenceWorkspaceApi.listFollowedStories({ limit: 100 }),
    enabled: isAuthenticated,
  });

  if (brief && savedList && followedList && !isLoading) {
  const clusterId = brief.id;
    setIsSaved(savedList.some((s) => s.story_cluster_id === clusterId));
    setIsFollowed(followedList.some((f) => f.story_cluster_id === clusterId));
  }

  if (isLoading) {
    return <BriefSkeleton />;
  }

  if (isError || !brief) {
    return (
      <div className="container-page py-16">
        <ErrorState
          message={error?.message ?? "Story not found."}
          retry={isError ? () => void refetch() : undefined}
        />
      </div>
    );
  }

  const clusterId = brief.id;

  async function handleSave() {
    if (!isAuthenticated) return;
    setSaving(true);
    try {
      await intelligenceWorkspaceApi.saveStory({ story_cluster_id: clusterId });
      setIsSaved(true);
      await queryClient.invalidateQueries({ queryKey: ["saved-stories"] });
    } catch {
      // handled
    } finally {
      setSaving(false);
    }
  }

  async function handleUnsave() {
    setSaving(true);
    try {
      await intelligenceWorkspaceApi.unsaveStory(clusterId);
      setIsSaved(false);
      await queryClient.invalidateQueries({ queryKey: ["saved-stories"] });
    } catch {
      // handled
    } finally {
      setSaving(false);
    }
  }

  async function handleFollow() {
    if (!isAuthenticated) return;
    setFollowing(true);
    try {
      await intelligenceWorkspaceApi.followStory(clusterId);
      setIsFollowed(true);
      await queryClient.invalidateQueries({ queryKey: ["followed-stories"] });
    } catch {
      // handled
    } finally {
      setFollowing(false);
    }
  }

  async function handleUnfollow() {
    setFollowing(true);
    try {
      await intelligenceWorkspaceApi.unfollowStory(clusterId);
      setIsFollowed(false);
      await queryClient.invalidateQueries({ queryKey: ["followed-stories"] });
    } catch {
      // handled
    } finally {
      setFollowing(false);
    }
  }

  const sources = brief.sources || [];
  const claims = brief.claims || [];
  const conflicts = brief.conflicts || [];
  const timeline = brief.timeline || [];
  const trends = brief.trends || [];
  const entities: BriefEntitiesContext = brief.entities || { companies: [], topics: [], graph_connections: [] };
  const relatedStories = brief.related_stories || [];
  const quality = brief.quality as BriefQualityIndicators | undefined;
  const provenance = brief.provenance;
  const storyEvolution = brief.story_evolution as BriefStoryEvolution | null | undefined;

  const statusBadgeTone = (status: string) => {
    switch (status.toLowerCase()) {
      case "breaking":
        return "danger";
      case "developing":
        return "warning";
      case "stale":
        return "neutral";
      default:
        return "brand";
    }
  };

  const activityBadgeTone = (activityStatus: string | null | undefined) => {
    if (!activityStatus) return "neutral";
    switch (activityStatus.toLowerCase()) {
      case "breaking":
        return "danger";
      case "developing":
        return "warning";
      case "dormant":
        return "neutral";
      default:
        return "brand";
    }
  };

  return (
    <>
      <Seo
        title={brief.title}
        description={
          brief.summary ||
          `Intelligence brief: ${brief.title}. ${brief.article_count} articles from ${brief.source_count} sources.`
        }
        ogType="article"
        canonical={`/stories/${brief.slug}`}
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
            <Badge tone={statusBadgeTone(brief.status)}>{brief.status}</Badge>
            {brief.activity_status && (
              <Badge tone={activityBadgeTone(brief.activity_status)}>
                {brief.activity_status}
              </Badge>
            )}
            {brief.importance_score != null && (
              <span className="text-sm text-slate-500">
                Importance: {brief.importance_score.toFixed(2)}
              </span>
            )}
            {brief.confidence != null && (
              <span className="text-sm text-slate-500">
                Confidence: {brief.confidence.toFixed(2)}
              </span>
            )}
            {provenance && (
              <ProvenanceBadge provenanceSource={provenance.source} />
            )}
            {isAuthenticated && (
              <>
                {isSaved ? (
                  <Button variant="ghost" size="sm" onClick={handleUnsave} disabled={saving}>
                    {saving ? "Removing..." : "Saved"}
                  </Button>
                ) : (
                  <Button variant="ghost" size="sm" onClick={handleSave} disabled={saving}>
                    {saving ? "Saving..." : "Save"}
                  </Button>
                )}
                {isFollowed ? (
                  <Button variant="ghost" size="sm" onClick={handleUnfollow} disabled={following}>
                    {following ? "Unfollowing..." : "Following"}
                  </Button>
                ) : (
                  <Button variant="ghost" size="sm" onClick={handleFollow} disabled={following}>
                    {following ? "Following..." : "Follow"}
                  </Button>
                )}
              </>
            )}
          </div>
          <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
            {brief.title}
          </h1>
          <p className="mt-3 text-sm text-slate-500">
            {brief.article_count} articles &middot; {brief.source_count} sources &middot;{" "}
            Updated {formatDateTime(brief.updated_at || brief.last_updated_at)}
            {brief.independent_source_count != null && brief.independent_source_count !== brief.source_count && (
              <span> &middot; {brief.independent_source_count} independent sources</span>
            )}
          </p>
        </header>

        {brief.summary && (
          <section className="mt-8 max-w-3xl" aria-labelledby="summary-heading">
            <h2 id="summary-heading" className="text-sm font-semibold uppercase tracking-wide text-brand-700">
              Executive Brief
            </h2>
            <p className="mt-2 text-slate-800 leading-relaxed">{brief.summary}</p>
          </section>
        )}

        {brief.key_takeaways && brief.key_takeaways.length > 0 && (
          <section className="mt-8 max-w-3xl" aria-labelledby="takeaways-heading">
            <h2 id="takeaways-heading" className="text-lg font-semibold text-slate-900">
              Key Takeaways
            </h2>
            <ul className="mt-3 list-inside list-disc space-y-1 text-slate-700">
              {brief.key_takeaways.map((takeaway, i) => (
                <li key={i}>{takeaway}</li>
              ))}
            </ul>
          </section>
        )}

        {brief.why_it_matters && (
          <section className="mt-8 max-w-3xl" aria-labelledby="why-heading">
            <h2 id="why-heading" className="text-lg font-semibold text-slate-900">
              Why It Matters
            </h2>
            <p className="mt-2 text-slate-700 leading-relaxed">{brief.why_it_matters}</p>
          </section>
        )}

        {quality && (
          <section className="mt-8 max-w-3xl" aria-labelledby="quality-heading">
            <h2 id="quality-heading" className="text-sm font-semibold uppercase tracking-wide text-brand-700">
              Intelligence Quality
            </h2>
            <div className="mt-3">
              <IntelligenceQualityPanel
                qualityFlags={quality.quality_flags}
                qualityExplanation={quality.quality_explanation}
                overallQualityScore={quality.overall_quality_score}
                provenanceComplete={provenance?.is_complete}
              />
              {quality.degraded && quality.degraded_message && (
                <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
                  {quality.degraded_message}
                </div>
              )}
            </div>
          </section>
        )}

        {sources.length > 0 && (
          <section className="mt-8 max-w-3xl" aria-labelledby="sources-heading">
            <h2 id="sources-heading" className="text-lg font-semibold text-slate-900">
              What Sources Say
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              {sources.length} publisher{sources.length === 1 ? "" : "s"} contributing to this story.
            </p>
            <div className="mt-4 space-y-6">
              {sources.map((source, idx) => (
                <div key={idx} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold text-slate-900">{source.publisher}</span>
                    <Badge tone="neutral">{source.source_type}</Badge>
                    <Badge>{source.source_role}</Badge>
                    {source.provenance_source && (
                      <ProvenanceBadge provenanceSource={source.provenance_source} />
                    )}
                    <span className="text-xs text-slate-500">
                      {source.article_count} article{source.article_count === 1 ? "" : "s"}
                    </span>
                  </div>
                  {source.articles && source.articles.length > 0 && (
                    <div className="mt-3 flex flex-col gap-3">
                      {source.articles.map((article, aIdx) => (
                        <div key={aIdx} className="text-sm">
                          <a
                            href={article.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="font-medium text-brand-700 hover:underline focus-visible:text-brand-700"
                          >
                            {article.headline}
                          </a>
                          <span className="ml-2 text-xs text-slate-500">
                            ({formatDateTime(article.publication_date)})
                          </span>
                          <span className="ml-2 text-xs text-brand-600">
                            Read original
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {claims.length > 0 && (
          <section className="mt-8 max-w-3xl" aria-labelledby="claims-heading">
            <h2 id="claims-heading" className="text-lg font-semibold text-slate-900">
              Claims &amp; Evidence
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Facts and reported claims backed by evidence from sources.
            </p>
            <div className="mt-4 space-y-4">
              {claims.map((claim, idx) => (
                <div key={idx} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={claim.status === "SUPPORTED" ? "success" : claim.status === "PARTIALLY_SUPPORTED" ? "warning" : claim.status === "UNSUPPORTED" ? "danger" : "neutral"}>
                      {claim.status}
                    </Badge>
                    <span className="text-xs text-slate-500">{claim.type}</span>
                    {claim.confidence != null && (
                      <span className="text-xs text-slate-500">
                        Confidence: {(claim.confidence * 100).toFixed(0)}%
                      </span>
                    )}
                     {claim.provenance_source && (
                       <ProvenanceBadge provenanceSource={claim.provenance_source} />
                     )}
                  </div>
                  <p className="mt-2 text-sm text-slate-800">{claim.claim_text}</p>
                  {claim.evidence && claim.evidence.length > 0 && (
                    <div className="mt-3 space-y-2">
                      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                        Evidence ({claim.evidence_count})
                      </p>
                      {claim.evidence.map((ev, eIdx) => (
                        <div
                          key={eIdx}
                          className="rounded-lg border border-slate-100 bg-slate-50 p-3 text-xs text-slate-700"
                        >
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge tone="neutral" className="text-xs">
                              {ev.evidence_type}
                            </Badge>
                            {ev.source_name && <span>{ev.source_name}</span>}
                            {ev.published_at && (
                              <span className="text-slate-500">
                                {formatDateTime(ev.published_at)}
                              </span>
                            )}
                          </div>
                          {ev.excerpt && <p className="mt-1 italic">&ldquo;{ev.excerpt}&rdquo;</p>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {claims.length === 0 && (
          <section className="mt-8 max-w-3xl">
            <EmptyState
              title="No claims extracted"
              description="Claims and evidence are extracted from source articles when available."
            />
          </section>
        )}

        {conflicts.length > 0 && (
          <section className="mt-8 max-w-3xl" aria-labelledby="conflicts-heading">
            <h2 id="conflicts-heading" className="text-lg font-semibold text-slate-900">
              Conflicts / Different Accounts
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Different sources report incompatible facts. This does not mean any source is wrong.
            </p>
            <div className="mt-3 space-y-4">
              {conflicts.map((c, idx) => (
                <div
                  key={idx}
                  className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">{c.explanation}</span>
                    <span className="text-xs text-amber-700">
                      {c.conflict_type}
                      {c.confidence != null && ` · ${(c.confidence * 100).toFixed(0)}%`}
                    </span>
                    <Badge tone="warning" className="text-xs">{c.status}</Badge>
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
          </section>
        )}

        {storyEvolution && (
          <section className="mt-8 max-w-3xl" aria-labelledby="evolution-heading">
            <h2 id="evolution-heading" className="text-lg font-semibold text-slate-900">
              Story Evolution
            </h2>
            <div className="mt-3 grid gap-4 sm:grid-cols-2">
              {storyEvolution.first_reported && (
                <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    First Reported
                  </p>
                  <p className="mt-1 text-sm font-medium text-slate-900">
                    {String(storyEvolution.first_reported.title || "")}
                  </p>
                  <p className="text-xs text-slate-500">
                    {storyEvolution.first_reported.published_at
                      ? formatDateTime(String(storyEvolution.first_reported.published_at))
                      : ""}
                  </p>
                  {storyEvolution.first_reported.source_name && (
                    <p className="text-xs text-slate-500">
                      {String(storyEvolution.first_reported.source_name)}
                    </p>
                  )}
                </div>
              )}
              {storyEvolution.latest_development && (
                <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Latest Development
                  </p>
                  <p className="mt-1 text-sm font-medium text-slate-900">
                    {String(storyEvolution.latest_development.title || "")}
                  </p>
                  <p className="text-xs text-slate-500">
                    {storyEvolution.latest_development.published_at
                      ? formatDateTime(String(storyEvolution.latest_development.published_at))
                      : ""}
                  </p>
                  {storyEvolution.latest_development.source_name && (
                    <p className="text-xs text-slate-500">
                      {String(storyEvolution.latest_development.source_name)}
                    </p>
                  )}
                </div>
              )}
            </div>
            {storyEvolution.major_developments && storyEvolution.major_developments.length > 0 && (
              <div className="mt-4">
                <h3 className="text-sm font-medium text-slate-700">Major Developments</h3>
                <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-slate-700">
                  {storyEvolution.major_developments.map((dev, i) => (
                    <li key={i}>{dev}</li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}

        {timeline.length > 0 && (
          <section className="mt-8 max-w-3xl" aria-labelledby="timeline-heading">
            <h2 id="timeline-heading" className="text-lg font-semibold text-slate-900">
              Timeline
            </h2>
            <div className="mt-4 space-y-3">
              {timeline.map((event: BriefTimelineItem) => (
                <div
                  key={event.id}
                  className="flex gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
                >
                  <div className="flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      {event.source_role && (
                        <Badge tone="brand" className="text-xs">{event.source_role}</Badge>
                      )}
                      {event.source_type && (
                        <Badge tone="neutral" className="text-xs">{event.source_type}</Badge>
                      )}
                      {event.published_at && (
                        <span className="text-xs text-slate-500">
                          {formatDateTime(event.published_at)}
                        </span>
                      )}
                    </div>
                    {event.title && (
                      <h3 className="mt-1 text-sm font-medium text-slate-900">
                        {event.url ? (
                          <a
                            href={event.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:text-brand-700 focus-visible:text-brand-700"
                          >
                            {event.title}
                          </a>
                        ) : (
                          event.title
                        )}
                      </h3>
                    )}
                    {event.summary && (
                      <p className="mt-1 text-xs text-slate-600">{event.summary}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {trends.length > 0 && (
          <section className="mt-8 max-w-3xl" aria-labelledby="trends-heading">
            <h2 id="trends-heading" className="text-lg font-semibold text-slate-900">
              Trend Context
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              This story is part of active trends:
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {trends.map((trend: BriefTrendContext) => (
                <Link
                  key={trend.id}
                  to={`/trends`}
                  className="rounded-full bg-brand-50 px-3 py-1 text-sm text-brand-800 hover:underline"
                >
                  {trend.display_name}
                </Link>
              ))}
            </div>
          </section>
        )}

        {(entities.companies?.length > 0 || entities.topics?.length > 0 || (entities.graph_connections && entities.graph_connections.length > 0)) && (
          <section className="mt-8 max-w-3xl" aria-labelledby="entities-heading">
            <h2 id="entities-heading" className="text-lg font-semibold text-slate-900">
              Entity Context
            </h2>
            {entities.companies && entities.companies.length > 0 && (
              <div className="mt-3">
                <h3 className="text-sm font-medium text-slate-700">Companies</h3>
                <div className="mt-2 flex flex-wrap gap-2">
                  {(entities.companies as BriefEntityContext[]).map((c) => (
                    <span
                      key={c.id}
                      className="rounded-full bg-brand-50 px-3 py-1 text-sm text-brand-800"
                    >
                      {c.name}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {entities.topics && entities.topics.length > 0 && (
              <div className="mt-4">
                <h3 className="text-sm font-medium text-slate-700">Topics</h3>
                <div className="mt-2 flex flex-wrap gap-2">
                  {(entities.topics as BriefEntityContext[]).map((t) => (
                    <span
                      key={t.id}
                      className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-800"
                    >
                      {t.name}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {entities.graph_connections && entities.graph_connections.length > 0 && (
              <div className="mt-4">
                <h3 className="text-sm font-medium text-slate-700">Connected Entities</h3>
                <div className="mt-2 space-y-2">
                  {(entities.graph_connections as BriefGraphConnection[]).map((conn, idx) => (
                    <div
                      key={idx}
                      className="rounded-lg border border-slate-200 bg-white p-3 text-sm"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium text-slate-900">{conn.name}</span>
                        <span className="text-xs text-slate-500">{conn.entity_type}</span>
                        {conn.relationship_type && (
                          <span className="rounded bg-brand-50 px-2 py-0.5 text-xs text-brand-700">
                            {conn.relationship_type}
                          </span>
                        )}
                        {conn.is_disputed && (
                          <span className="rounded bg-amber-50 px-2 py-0.5 text-xs text-amber-700">
                            disputed
                          </span>
                        )}
                        {conn.is_retracted && (
                          <span className="rounded bg-red-50 px-2 py-0.5 text-xs text-red-700">
                            retracted
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-xs text-slate-500">{conn.explanation}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}

        {relatedStories.length > 0 && (
          <section className="mt-8 max-w-3xl" aria-labelledby="related-heading">
            <h2 id="related-heading" className="text-lg font-semibold text-slate-900">
              Related Stories
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Stories semantically or graph-connected to this one.
            </p>
            <div className="mt-3 flex flex-col gap-3">
              {relatedStories.map((story: BriefRelatedStoryItem) => (
                <Link
                  key={story.cluster_id}
                  to={`/stories/${story.cluster_id}`}
                  className="block rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:border-brand-300 focus-visible:border-brand-300"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-slate-900">{story.title}</span>
                    <Badge tone="neutral" className="text-xs">
                      {story.article_count} articles
                    </Badge>
                    <Badge tone="neutral" className="text-xs">
                      {story.source_count} sources
                    </Badge>
                  </div>
                  {story.summary && (
                    <p className="mt-1 text-sm text-slate-600">{story.summary}</p>
                  )}
                  <p className="mt-1 text-xs text-slate-500">{story.reason}</p>
                </Link>
              ))}
            </div>
          </section>
        )}

        {relatedStories.length === 0 && (
          <section className="mt-8 max-w-3xl">
            <EmptyState
              title="No related stories"
              description="There are no semantically related stories at this time."
            />
          </section>
        )}

        {provenance && (
          <section className="mt-8 max-w-3xl">
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                Provenance
              </h2>
              <div className="mt-2 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
                <div>
                  <span className="font-medium">Source type:</span> {provenance.source}
                </div>
                <div>
                  <span className="font-medium">Articles:</span> {provenance.article_count}
                </div>
                <div>
                  <span className="font-medium">AI-generated:</span> {provenance.ai_generated_count}
                </div>
                <div>
                  <span className="font-medium">Deterministic:</span> {provenance.deterministic_count}
                </div>
                <div>
                  <span className="font-medium">Complete:</span>{" "}
                  {provenance.is_complete ? "Yes" : "No"}
                </div>
                {provenance.completeness_gaps && provenance.completeness_gaps.length > 0 && (
                  <div className="sm:col-span-2">
                    <span className="font-medium">Gaps:</span>{" "}
                    {provenance.completeness_gaps.join(", ")}
                  </div>
                )}
              </div>
            </div>
          </section>
        )}
      </article>
    </>
  );
}
