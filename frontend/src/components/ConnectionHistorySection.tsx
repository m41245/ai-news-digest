import { useQuery } from "@tanstack/react-query";
import { publicApi } from "../api";
import { Badge } from "./ui/Badge";
import { EmptyState } from "./ui/EmptyState";
import { Skeleton } from "./ui/Skeleton";
import { formatDateTime } from "../utils";

interface ConnectionHistorySectionProps {
  clusterId: string;
  clusterTitle: string;
}

export function ConnectionHistorySection({
  clusterId,
  clusterTitle,
}: ConnectionHistorySectionProps) {
  const { data: evolution, isLoading: evolutionLoading } = useQuery({
    queryKey: ["storyClusterEvolution", clusterId],
    queryFn: () =>
      publicApi.entityEvolution("story", clusterId),
    enabled: !!clusterId,
  });

  const { data: changes, isLoading: changesLoading } = useQuery({
    queryKey: ["storyClusterChanges", clusterId],
    queryFn: () =>
      publicApi.entityRelationshipChanges("story", clusterId),
    enabled: !!clusterId,
  });

  if (evolutionLoading || changesLoading) {
    return (
      <div className="mt-8 max-w-3xl">
        <h2 className="text-lg font-semibold text-slate-900">Connection History</h2>
        <Skeleton className="h-4 w-full mt-4" />
        <Skeleton className="h-4 w-5/6 mt-2" />
      </div>
    );
  }

  const hasEvolution =
    evolution &&
    (evolution.new_connections.length > 0 ||
      evolution.recently_active.length > 0 ||
      evolution.historical_connections.length > 0);

  const hasChanges = changes && changes.length > 0;

  if (!hasEvolution && !hasChanges) {
    return (
      <div className="mt-8 max-w-3xl">
        <h2 className="text-lg font-semibold text-slate-900">Connection History</h2>
        <EmptyState
          title="No connection history"
          description="Connection history will appear here as relationships are observed over time."
        />
      </div>
    );
  }

  return (
    <div className="mt-8 max-w-3xl">
      <h2 className="text-lg font-semibold text-slate-900">Connection History</h2>
      <p className="mt-1 text-sm text-slate-500">
        How &quot;{clusterTitle}&quot; connections have changed over time.
      </p>

      {hasChanges && (
        <div className="mt-4">
          <h3 className="text-sm font-medium text-slate-700">Recent Changes</h3>
          <div className="mt-2 space-y-2">
            {changes!.slice(0, 10).map((change, idx: number) => (
              <div
                key={idx}
                className="rounded-lg border border-slate-200 bg-white p-3 text-sm"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-slate-900">{change.object_name}</span>
                  <span className="text-xs text-slate-500">{change.relationship_type}</span>
                  <Badge
                    tone={
                      change.change_type === "new_connection"
                        ? "success"
                        : change.change_type === "became_stale"
                        ? "neutral"
                        : "brand"
                    }
                  >
                    {change.change_type.replace(/_/g, " ")}
                  </Badge>
                </div>
                <p className="mt-1 text-xs text-slate-500">{change.explanation}</p>
                {change.observed_at && (
                  <p className="mt-1 text-xs text-slate-400">
                    {formatDateTime(change.observed_at)}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {hasEvolution && (
        <div className="mt-6">
          <h3 className="text-sm font-medium text-slate-700">Current State</h3>
          <div className="mt-2 grid gap-4 sm:grid-cols-3">
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-2xl font-bold text-slate-900">
                {evolution!.new_connections.length}
              </p>
              <p className="text-sm text-slate-500">New Connections</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-2xl font-bold text-slate-900">
                {evolution!.recently_active.length}
              </p>
              <p className="text-sm text-slate-500">Recently Active</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-2xl font-bold text-slate-900">
                {evolution!.historical_connections.length}
              </p>
              <p className="text-sm text-slate-500">Historical</p>
            </div>
          </div>
        </div>
      )}

      {evolution && (
        <p className="mt-4 text-xs text-slate-400">
          Generated {formatDateTime(evolution.generated_at)}
        </p>
      )}
    </div>
  );
}
