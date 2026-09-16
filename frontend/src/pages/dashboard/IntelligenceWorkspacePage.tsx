import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { publicApi } from "../../api";
import { intelligenceWorkspaceApi } from "../../api";
import { Seo } from "../../components/Seo";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Spinner } from "../../components/ui/Spinner";
import { StoryCard } from "../../components/StoryCard";
import { formatDateTime } from "../../utils";
import { useAuth } from "../../auth/AuthContext";
import type { SavedStoryResponse, FollowedStoryResponse } from "../../types";

export function IntelligenceWorkspacePage() {
  const { user } = useAuth();

  const { data: saved, isLoading: savedLoading, refetch: refetchSaved } = useQuery({
    queryKey: ["saved-stories"],
    queryFn: () => intelligenceWorkspaceApi.listSavedStories({ limit: 5 }),
    enabled: !!user,
  });

  const { data: followed, isLoading: followedLoading, refetch: refetchFollowed } = useQuery({
    queryKey: ["followed-stories"],
    queryFn: () => intelligenceWorkspaceApi.listFollowedStories({ limit: 5 }),
    enabled: !!user,
  });

  const { data: topStory } = useQuery({
    queryKey: ["top-story"],
    queryFn: () => publicApi.topStory(),
  });

  const savedCount = saved?.length ?? 0;
  const followedCount = followed?.length ?? 0;

  return (
    <>
      <Seo title="My Intelligence" noindex />
      <div className="container-page py-8">
        <div className="mb-8 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">My Intelligence</h1>
            <p className="mt-1 text-slate-600">
              Welcome back{user?.email ? `, ${user.email}` : ""}.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="secondary">
              <Link to="/me/saved" className="inline-flex">
                Saved ({savedCount})
              </Link>
            </Button>
            <Button variant="secondary">
              <Link to="/me/following" className="inline-flex">
                Following ({followedCount})
              </Link>
            </Button>
            <Button>
              <Link to="/me/feed" className="inline-flex">
                Your Feed
              </Link>
            </Button>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6">
            {topStory?.title && (
              <Card>
                <h2 className="text-lg font-semibold text-slate-900">Top Story</h2>
                <div className="mt-3">
                  <StoryCard
                    story={{
                      headline: topStory.title,
                      summary: topStory.summary || "",
                      key_takeaways: [],
                      why_it_matters: undefined,
                      activity_status: topStory.activity_status || undefined,
                    }}
                    index={0}
                  />
                  {topStory.slug && (
                    <Link
                      to={`/stories/${topStory.slug}`}
                      className="mt-2 text-sm font-medium text-brand-600 hover:underline"
                    >
                      Read full story brief &rarr;
                    </Link>
                  )}
                </div>
              </Card>
            )}

            <Card>
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-900">Saved Stories</h2>
                <Link to="/me/saved" className="text-sm font-medium text-brand-600 hover:underline">
                  View all
                </Link>
              </div>
              {savedLoading ? (
                <Spinner label="Loading saved stories" />
              ) : saved && saved.length > 0 ? (
                <div className="mt-4 space-y-3">
                  {saved.slice(0, 3).map((s) => (
                    <SavedStoryRow key={s.id} saved={s} onChanged={() => void refetchSaved()} />
                  ))}
                </div>
              ) : (
                <p className="mt-4 text-sm text-slate-500">No saved stories yet. Save stories from the story brief page.</p>
              )}
            </Card>

            <Card>
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-900">Following</h2>
                <Link to="/me/following" className="text-sm font-medium text-brand-600 hover:underline">
                  View all
                </Link>
              </div>
              {followedLoading ? (
                <Spinner label="Loading followed stories" />
              ) : followed && followed.length > 0 ? (
                <div className="mt-4 space-y-3">
                  {followed.slice(0, 3).map((f) => (
                    <FollowedStoryRow key={f.id} followed={f} onChanged={() => void refetchFollowed()} />
                  ))}
                </div>
              ) : (
                <p className="mt-4 text-sm text-slate-500">Not following any stories yet. Follow stories from the story brief page.</p>
              )}
            </Card>
          </div>

          <div className="space-y-6">
            <Card>
              <h2 className="text-lg font-semibold text-slate-900">Your Account</h2>
              <dl className="mt-4 flex flex-col gap-3 text-sm">
                <div className="flex justify-between">
                  <dt className="text-slate-500">Email</dt>
                  <dd className="font-medium text-slate-900">{user?.email}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Role</dt>
                  <dd className="font-medium text-slate-900">
                    {user?.is_admin ? "Administrator" : "Member"}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Saved</dt>
                  <dd className="font-medium text-slate-900">{savedCount}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Following</dt>
                  <dd className="font-medium text-slate-900">{followedCount}</dd>
                </div>
              </dl>
            </Card>
          </div>
        </div>
      </div>
    </>
  );
}

function SavedStoryRow({ saved, onChanged }: { saved: SavedStoryResponse; onChanged: () => void }) {
  const [unsaving, setUnsaving] = useState(false);

  async function handleUnsave() {
    setUnsaving(true);
    try {
      await intelligenceWorkspaceApi.unsaveStory(saved.story_cluster_id);
      onChanged();
    } catch {
      // handled by global error boundary
    } finally {
      setUnsaving(false);
    }
  }

  return (
    <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex-1 min-w-0">
        <Link to={`/stories/${saved.story_cluster_id}`} className="text-sm font-medium text-brand-700 hover:underline truncate block">
          {saved.story_cluster_id}
        </Link>
        <p className="text-xs text-slate-500">Saved {formatDateTime(saved.created_at)}</p>
        {saved.note && <p className="text-xs text-slate-600 mt-1">{saved.note}</p>}
      </div>
      <Button variant="ghost" size="sm" onClick={handleUnsave} disabled={unsaving}>
        {unsaving ? "Removing..." : "Unsave"}
      </Button>
    </div>
  );
}

function FollowedStoryRow({ followed, onChanged }: { followed: FollowedStoryResponse; onChanged: () => void }) {
  const [unfollowing, setUnfollowing] = useState(false);

  async function handleUnfollow() {
    setUnfollowing(true);
    try {
      await intelligenceWorkspaceApi.unfollowStory(followed.story_cluster_id);
      onChanged();
    } catch {
      // handled
    } finally {
      setUnfollowing(false);
    }
  }

  return (
    <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex-1 min-w-0">
        <Link to={`/stories/${followed.story_cluster_id}`} className="text-sm font-medium text-brand-700 hover:underline truncate block">
          {followed.story_cluster_id}
        </Link>
        <p className="text-xs text-slate-500">Following since {formatDateTime(followed.created_at)}</p>
      </div>
      <Button variant="ghost" size="sm" onClick={handleUnfollow} disabled={unfollowing}>
        {unfollowing ? "Unfollowing..." : "Unfollow"}
      </Button>
    </div>
  );
}