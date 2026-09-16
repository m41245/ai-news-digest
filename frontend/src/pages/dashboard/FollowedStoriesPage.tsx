import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { intelligenceWorkspaceApi } from "../../api";
import { publicApi } from "../../api";
import { Seo } from "../../components/Seo";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { ErrorState } from "../../components/ui/ErrorState";
import { EmptyState } from "../../components/ui/EmptyState";
import { ListSkeleton } from "../../components/ui/Skeleton";
import { Badge } from "../../components/ui/Badge";
import { formatDateTime } from "../../utils";
import type { PublicStoryClusterSearch } from "../../types";

export function FollowedStoriesPage() {
  const queryClient = useQueryClient();

  const { data: followed, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["followed-stories"],
    queryFn: () => intelligenceWorkspaceApi.listFollowedStories({ limit: 50 }),
  });

  const storyIds = (followed || []).map((f) => f.story_cluster_id);
  const { data: stories } = useQuery({
    queryKey: ["followed-story-details", storyIds],
    queryFn: async () => {
      if (storyIds.length === 0) return [];
      const results = await Promise.all(
        storyIds.map((id) =>
          publicApi
            .storyCluster(id)
            .catch(() => null),
        ),
      );
      return results.filter(Boolean) as PublicStoryClusterSearch[];
    },
    enabled: storyIds.length > 0,
  });

  async function handleUnfollow(story_cluster_id: string) {
    await intelligenceWorkspaceApi.unfollowStory(story_cluster_id);
    await queryClient.invalidateQueries({ queryKey: ["followed-stories"] });
  }

  const storyMap = new Map(stories?.map((s) => [s.id, s]));

  return (
    <>
      <Seo title="Following" noindex />
      <div className="container-page py-8">
        <div className="mb-8 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Following</h1>
            <p className="mt-1 text-slate-600">Stories you&apos;re tracking for updates.</p>
          </div>
          <div className="flex gap-2">
            <Link to="/me">
              <Button variant="secondary">&larr; Back to workspace</Button>
            </Link>
          </div>
        </div>

        {isError && (
          <ErrorState
            message={error?.message ?? "Failed to load followed stories."}
            retry={() => void refetch()}
          />
        )}

        {isLoading ? (
          <ListSkeleton rows={5} />
        ) : followed && followed.length > 0 ? (
          <div className="grid gap-4">
            {followed.map((f) => {
              const story = storyMap.get(f.story_cluster_id);
              return (
                <Card key={f.id}>
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      {story ? (
                        <>
                          <Link
                            to={`/stories/${story.slug}`}
                            className="text-base font-medium text-brand-700 hover:underline"
                          >
                            {story.title}
                          </Link>
                          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                            <Badge tone={story.status === "ACTIVE" ? "brand" : "neutral"}>{story.status}</Badge>
                            {story.importance_score != null && (
                              <span>Importance: {story.importance_score.toFixed(2)}</span>
                            )}
                            {story.article_count != null && <span>{story.article_count} articles</span>}
                            {story.source_count != null && <span>{story.source_count} sources</span>}
                          </div>
                          {story.summary && (
                            <p className="mt-2 text-sm text-slate-700 line-clamp-2">{story.summary}</p>
                          )}
                          <p className="mt-1 text-xs text-slate-500">Updated {formatDateTime((story as unknown as { updated_at?: string; last_updated_at?: string }).updated_at || (story as unknown as { updated_at?: string; last_updated_at?: string }).last_updated_at || story.first_published_at)}</p>
                        </>
                      ) : (
                        <div>
                          <Link
                            to={`/stories/${f.story_cluster_id}`}
                            className="text-base font-medium text-brand-700 hover:underline"
                          >
                            {f.story_cluster_id}
                          </Link>
                          <p className="mt-1 text-xs text-slate-500">Following since {formatDateTime(f.created_at)}</p>
                        </div>
                      )}
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleUnfollow(f.story_cluster_id)}
                    >
                      Unfollow
                    </Button>
                  </div>
                </Card>
              );
            })}
          </div>
        ) : (
          <EmptyState
            title="Not following any stories"
            description="Follow stories from the story brief page to track their evolution."
          />
        )}
      </div>
    </>
  );
}
