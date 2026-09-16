import { useQuery } from "@tanstack/react-query";
import { publicApi } from "../api";
import { Badge } from "./ui/Badge";
import { EmptyState } from "./ui/EmptyState";
import { Skeleton } from "./ui/Skeleton";
import { formatDateTime } from "../utils";

interface ChangeEvent {
  object_name: string;
  relationship_type: string;
  change_type: string;
  explanation: string;
  observed_at?: string | null;
}

interface RelationshipEvolutionSectionProps {
  entityType: "company" | "topic" | "story" | "category" | "article";
  entityId: string;
  entityName: string;
}

export function RelationshipEvolutionSection({
  entityType,
  entityId,
  entityName,
}: RelationshipEvolutionSectionProps) {
  const { data: evolution, isLoading, isError, error } = useQuery({
    queryKey: ["entityEvolution", entityType, entityId],
    queryFn: () => publicApi.entityEvolution(entityType, entityId),
  });

  const { data: changes } = useQuery({
    queryKey: ["entityChanges", entityType, entityId],
    queryFn: () => publicApi.entityRelationshipChanges(entityType, entityId),
  });

  if (isLoading) {
    return (
      <div className="mt-8 max-w-3xl">
        <h2 className="text-lg font-semibold text-slate-900">Relationship Evolution</h2>
        <Skeleton className="h-4 w-full mt-4" />
        <Skeleton className="h-4 w-5/6 mt-2" />
      </div>
    );
  }

  if (isError || !evolution) {
    return (
      <div className="mt-8 max-w-3xl">
        <h2 className="text-lg font-semibold text-slate-900">Relationship Evolution</h2>
        <p className="mt-2 text-sm text-slate-500">
          {error?.message ?? "Unable to load relationship evolution."}
        </p>
      </div>
    );
  }

  const hasContent =
    evolution.new_connections.length > 0 ||
    evolution.recently_active.length > 0 ||
    evolution.recently_changed.length > 0 ||
    evolution.historical_connections.length > 0;

  if (!hasContent) {
    return (
      <div className="mt-8 max-w-3xl">
        <h2 className="text-lg font-semibold text-slate-900">Relationship Evolution</h2>
        <EmptyState
          title="No evolution data"
          description="Relationship evolution will appear here as connections are observed over time."
        />
      </div>
    );
  }

  return (
    <div className="mt-8 max-w-3xl">
      <h2 className="text-lg font-semibold text-slate-900">Relationship Evolution</h2>
      <p className="mt-1 text-sm text-slate-500">
        How {entityName}&apos;s connections have changed over time.
      </p>

      {evolution.new_connections.length > 0 && (
        <div className="mt-4">
          <h3 className="text-sm font-medium text-slate-700">New Connections</h3>
          <div className="mt-2 space-y-2">
            {evolution.new_connections.slice(0, 5).map((conn, idx: number) => (
              <div
                key={idx}
                className="rounded-lg border border-slate-200 bg-white p-3 text-sm"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-slate-900">{conn.name as string}</span>
                  <span className="text-xs text-slate-500">{conn.entity_type as string}</span>
                  {(conn.relationship_type as string | null) && (
                    <span className="rounded bg-brand-50 px-2 py-0.5 text-xs text-brand-700">
                      {conn.relationship_type as string}
                    </span>
                  )}
                  <Badge tone="success">New</Badge>
                </div>
                {(conn.first_observed_at as string | null) && (
                  <p className="mt-1 text-xs text-slate-500">
                    First observed {formatDateTime(conn.first_observed_at as string)}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {evolution.recently_active.length > 0 && (
        <div className="mt-4">
          <h3 className="text-sm font-medium text-slate-700">Recently Active</h3>
          <div className="mt-2 space-y-2">
            {evolution.recently_active.slice(0, 5).map((conn, idx: number) => (
              <div
                key={idx}
                className="rounded-lg border border-slate-200 bg-white p-3 text-sm"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-slate-900">{conn.name as string}</span>
                  <span className="text-xs text-slate-500">{conn.entity_type as string}</span>
                  {(conn.relationship_type as string | null) && (
                    <span className="rounded bg-brand-50 px-2 py-0.5 text-xs text-brand-700">
                      {conn.relationship_type as string}
                    </span>
                  )}
                  <Badge tone="brand">Active</Badge>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  {conn.observation_count as number} observations &middot;{" "}
                  {conn.source_count as number} sources
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {evolution.historical_connections.length > 0 && (
        <div className="mt-4">
          <h3 className="text-sm font-medium text-slate-700">Historical Connections</h3>
          <div className="mt-2 space-y-2">
            {evolution.historical_connections.slice(0, 5).map((conn, idx: number) => (
              <div
                key={idx}
                className="rounded-lg border border-slate-200 bg-white p-3 text-sm"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-slate-900">{conn.name as string}</span>
                  <span className="text-xs text-slate-500">{conn.entity_type as string}</span>
                  {(conn.relationship_type as string | null) && (
                    <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-700">
                      {conn.relationship_type as string}
                    </span>
                  )}
                  <Badge tone="neutral">Historical</Badge>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  Last observed {conn.last_observed_at ? formatDateTime(conn.last_observed_at as string) : "unknown"}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {changes && changes.length > 0 && (
        <div className="mt-6">
          <h3 className="text-sm font-medium text-slate-700">Recent Changes</h3>
          <div className="mt-2 space-y-2">
            {changes.slice(0, 10).map((change: ChangeEvent, idx: number) => (
              <div
                key={idx}
                className="rounded-lg border border-slate-200 bg-white p-3 text-sm"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-slate-900">{change.object_name}</span>
                  <span className="text-xs text-slate-500">{change.relationship_type}</span>
                  <Badge tone={change.change_type === "new_connection" ? "success" : change.change_type === "became_stale" ? "neutral" : "brand"}>
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

      <p className="mt-4 text-xs text-slate-400">
        Generated {formatDateTime(evolution.generated_at)}
      </p>
    </div>
  );
}
