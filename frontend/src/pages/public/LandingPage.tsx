import { Helmet } from "react-helmet-async";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { publicApi } from "../../api";
import { TopStoryCard } from "../../components/TopStoryCard";
import { DigestCard } from "../../components/DigestCard";
import { EmptyState } from "../../components/ui/EmptyState";
import { Skeleton } from "../../components/ui/Skeleton";

function TopStorySkeleton() {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-col gap-3">
        <Skeleton className="h-5 w-24" />
        <Skeleton className="h-6 w-3/4" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-2/3" />
        <div className="flex gap-3">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-3 w-24" />
        </div>
      </div>
    </div>
  );
}

function DigestSkeleton() {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <Skeleton className="h-5 w-16" />
          <Skeleton className="h-3 w-20" />
        </div>
        <Skeleton className="h-5 w-2/3" />
        <Skeleton className="h-3 w-24" />
      </div>
    </div>
  );
}

export function LandingPage() {
  const { data: topStoryData, isLoading: topStoryLoading } = useQuery({
    queryKey: ["topStory"],
    queryFn: () => publicApi.topStory(),
  });

  const { data: digestsData, isLoading: digestsLoading } = useQuery({
    queryKey: ["digests", 1],
    queryFn: () => publicApi.digests({ limit: 3, offset: 0 }),
  });

  const latestDigest = digestsData?.items?.[0];

  const topStory = topStoryData?.top_story_cluster_id
    ? {
        cluster_id: topStoryData.top_story_cluster_id,
        title: topStoryData.title || "Top Story",
        slug: topStoryData.slug || "",
        summary: topStoryData.summary,
        importance_score: topStoryData.importance_score,
        confidence: topStoryData.confidence,
        ranking_score: topStoryData.top_story_score,
        ranking_explanation: null,
      }
    : null;

  return (
    <>
      <Helmet>
        <title>AI News Digest — News distilled by AI</title>
        <meta
          name="description"
          content="AI-powered news aggregation, summarization, and daily digests. Stay informed with curated, categorized news delivered in a clear, readable format."
        />
        <meta property="og:type" content="website" />
        <meta property="og:title" content="AI News Digest — News distilled by AI" />
        <meta property="og:site_name" content="AI News Digest" />
        <meta property="og:description" content="AI-powered news aggregation, summarization, and daily digests." />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="AI News Digest — News distilled by AI" />
        <meta name="twitter:description" content="AI-powered news aggregation, summarization, and daily digests." />
        <link rel="canonical" href="/" />
      </Helmet>
      <section className="container-page py-20 sm:py-28">
        <div className="mx-auto max-w-3xl text-center">
          <span className="inline-flex items-center rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700">
            AI-powered news, curated daily
          </span>
          <h1 className="mt-6 text-4xl font-bold tracking-tight text-slate-900 sm:text-6xl">
            News, distilled by AI.
          </h1>
          <p className="mt-6 text-lg leading-relaxed text-slate-600">
            AI News Digest aggregates articles from trusted sources, summarizes
            them with AI, and delivers clear, categorized daily digests so you
            can stay informed without the noise.
          </p>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
            <Link
              to="/news"
              className="inline-flex items-center justify-center rounded-lg bg-brand-600 px-5 py-2.5 text-base font-medium text-white shadow-sm transition-colors hover:bg-brand-700"
            >
              Browse the latest news
            </Link>
            <Link
              to="/digests"
              className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-5 py-2.5 text-base font-medium text-slate-900 shadow-sm transition-colors hover:bg-slate-50"
            >
              View digests
            </Link>
          </div>
        </div>
      </section>

      {(topStoryLoading || digestsLoading) && (
        <section className="border-t border-slate-200 bg-slate-50 py-16">
          <div className="container-page">
            <div className="mx-auto max-w-3xl">
              <div className="mb-8">
                <Skeleton className="h-7 w-32" />
                <Skeleton className="mt-2 h-4 w-64" />
              </div>
              <div className="mb-12">
                <TopStorySkeleton />
              </div>
              <div>
                <div className="mb-6">
                  <Skeleton className="h-7 w-32" />
                  <Skeleton className="mt-2 h-4 w-64" />
                </div>
                <div className="flex flex-col gap-4">
                  <DigestSkeleton />
                  <DigestSkeleton />
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      {!(topStoryLoading || digestsLoading) && (
        <>
          {topStory && (
            <section className="border-t border-slate-200 bg-slate-50 py-16">
              <div className="container-page">
                <div className="mx-auto mb-8 max-w-3xl">
                  <h2 className="text-2xl font-bold text-slate-900">Top Story</h2>
                  <p className="mt-2 text-slate-600">
                    The most important AI story right now, ranked by our intelligence engine.
                  </p>
                </div>
                <div className="mx-auto max-w-3xl">
                  <TopStoryCard story={topStory} />
                </div>
              </div>
            </section>
          )}

          {latestDigest && (
            <section className="border-t border-slate-200 py-16">
              <div className="container-page">
                <div className="mx-auto mb-8 flex items-end justify-between">
                  <div>
                    <h2 className="text-2xl font-bold text-slate-900">Latest Digest</h2>
                    <p className="mt-2 text-slate-600">
                      The most recent AI-curated news summary.
                    </p>
                  </div>
                  <Link
                    to="/digests"
                    className="text-sm font-medium text-brand-600 hover:underline"
                  >
                    View all digests
                  </Link>
                </div>
                <div className="mx-auto max-w-3xl">
                  <DigestCard digest={latestDigest} />
                  {latestDigest.top_story && (
                    <div className="mt-6">
                      <h3 className="text-lg font-semibold text-slate-900 mb-3">Top Story in this Digest</h3>
                      <TopStoryCard story={latestDigest.top_story} digestId={latestDigest.id} />
                    </div>
                  )}
                </div>
              </div>
            </section>
          )}
        </>
      )}

      {!topStoryLoading && !digestsLoading && !topStory && !latestDigest && (
        <section className="border-t border-slate-200 bg-slate-50 py-16">
          <div className="container-page">
            <EmptyState
              title="No digests yet"
              description="Digests appear here once the daily generation pipeline runs."
            />
          </div>
        </section>
      )}

      <section className="container-page py-16">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-2xl font-bold text-slate-900">
            Ready to cut through the noise?
          </h2>
          <p className="mt-2 text-slate-600">
            Explore the latest articles and digests, or sign up for a
            personalized experience.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link
              to="/news"
              className="inline-flex items-center justify-center rounded-lg bg-brand-600 px-5 py-2.5 text-base font-medium text-white shadow-sm transition-colors hover:bg-brand-700"
            >
              Explore news
            </Link>
            <Link
              to="/register"
              className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-5 py-2.5 text-base font-medium text-slate-900 shadow-sm transition-colors hover:bg-slate-50"
            >
              Create an account
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
