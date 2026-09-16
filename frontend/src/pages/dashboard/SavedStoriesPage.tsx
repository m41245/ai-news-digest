import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { intelligenceWorkspaceApi } from "../../api";
import { Seo } from "../../components/Seo";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { ErrorState } from "../../components/ui/ErrorState";
import { EmptyState } from "../../components/ui/EmptyState";
import { ListSkeleton } from "../../components/ui/Skeleton";
import { formatDateTime } from "../../utils";

export function SavedStoriesPage() {
  const queryClient = useQueryClient();
  const [collectionFilter, setCollectionFilter] = useState<string>("");

  const { data: collections } = useQuery({
    queryKey: ["collections"],
    queryFn: () => intelligenceWorkspaceApi.listCollections({ limit: 50 }),
  });

  const { data: saved, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["saved-stories", collectionFilter],
    queryFn: () =>
      intelligenceWorkspaceApi.listSavedStories({
        collection_id: collectionFilter || undefined,
        limit: 20,
      }),
  });

  async function handleUnsave(story_cluster_id: string) {
    await intelligenceWorkspaceApi.unsaveStory(story_cluster_id);
    await queryClient.invalidateQueries({ queryKey: ["saved-stories"] });
  }

  return (
    <>
      <Seo title="Saved Stories" noindex />
      <div className="container-page py-8">
        <div className="mb-8 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Saved Stories</h1>
            <p className="mt-1 text-slate-600">Stories you&apos;ve saved for later reference.</p>
          </div>
          <div className="flex gap-2">
            <Link to="/me">
              <Button variant="secondary">&larr; Back to workspace</Button>
            </Link>
          </div>
        </div>

        {collections && collections.length > 0 && (
          <div className="mb-6">
            <label className="block text-sm font-medium text-slate-700 mb-1">Filter by collection</label>
            <select
              value={collectionFilter}
              onChange={(e) => setCollectionFilter(e.target.value)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              <option value="">All saved stories</option>
              {collections.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
        )}

        {isError && (
          <ErrorState
            message={error?.message ?? "Failed to load saved stories."}
            retry={() => void refetch()}
          />
        )}

        {isLoading ? (
          <ListSkeleton rows={5} />
        ) : saved && saved.length > 0 ? (
          <div className="grid gap-4">
            {saved.map((s) => (
              <Card key={s.id}>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <Link
                      to={`/stories/${s.story_cluster_id}`}
                      className="text-base font-medium text-brand-700 hover:underline"
                    >
                      {s.story_cluster_id}
                    </Link>
                    <p className="mt-1 text-xs text-slate-500">Saved {formatDateTime(s.created_at)}</p>
                    {s.note && (
                      <p className="mt-2 text-sm text-slate-700 bg-slate-50 rounded-lg p-3">{s.note}</p>
                    )}
                    {s.collection_id && (
                      <span className="mt-2 inline-block rounded-full bg-brand-50 px-2 py-1 text-xs text-brand-800">
                        {collections?.find((c) => c.id === s.collection_id)?.name || s.collection_id}
                      </span>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleUnsave(s.story_cluster_id)}
                  >
                    Unsave
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No saved stories"
            description="Save stories from the story brief page to build your personal intelligence library."
          />
        )}
      </div>
    </>
  );
}
