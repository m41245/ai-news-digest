import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Seo } from "../../components/Seo";
import { publicApi } from "../../api";
import { Spinner } from "../../components/ui/Spinner";
import { ErrorState } from "../../components/ui/ErrorState";
import { TopStoryCard } from "../../components/TopStoryCard";
import { StoryCard } from "../../components/StoryCard";
import { formatDateTime } from "../../utils";

export function DigestDetailPage() {
  const { id } = useParams<{ id: string }>();

  const { data: digest, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["digest", id],
    queryFn: () => publicApi.digest(id!),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="container-page py-16">
        <Spinner label="Loading digest" />
      </div>
    );
  }

  if (isError || !digest) {
    return (
      <div className="container-page py-16">
        <ErrorState
          message={error?.message ?? "Digest not found."}
          retry={isError ? () => void refetch() : undefined}
        />
      </div>
    );
  }

  return (
    <>
      <Seo
        title={digest.title}
        description={`Daily digest with ${digest.article_count} articles.`}
        ogType="article"
        canonical={`/digests/${digest.id}`}
      />
      <article className="container-page py-8">
        <Link
          to="/digests"
          className="text-sm font-medium text-brand-600 hover:underline"
        >
          &larr; Back to digests
        </Link>
        <header className="mt-4 max-w-3xl">
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
            {digest.title}
          </h1>
          <p className="mt-3 text-sm text-slate-500">
            Generated {formatDateTime(digest.generated_at)} &middot;{" "}
            {digest.article_count} article
            {digest.article_count === 1 ? "" : "s"} &middot;{" "}
            {digest.format.toLowerCase()}
          </p>
        </header>

        {digest.top_story && (
          <div className="mt-8 max-w-3xl">
            <h2 className="text-2xl font-bold text-slate-900 mb-4">Top Story</h2>
            <TopStoryCard story={digest.top_story} digestId={digest.id} />
          </div>
        )}

        <div className="mt-8 max-w-3xl">
          <div className="prose-body whitespace-pre-wrap rounded-xl border border-slate-200 bg-white p-6 text-base shadow-sm">
            {digest.content}
          </div>
        </div>

        {digest.stories && digest.stories.length > 0 && (
          <div className="mt-12 max-w-3xl">
            <h2 className="text-2xl font-bold text-slate-900 mb-6">Stories</h2>
            <div className="flex flex-col gap-6">
              {digest.stories.map((story, index) => (
                <StoryCard
                  key={story.cluster_id || index}
                  story={story}
                  index={index}
                  digestId={digest.id}
                />
              ))}
            </div>
          </div>
        )}
      </article>
    </>
  );
}
