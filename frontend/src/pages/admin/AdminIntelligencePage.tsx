import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Seo } from "../../components/Seo";
import { Card } from "../../components/ui/Card";
import { adminApi } from "../../api";
import { ListSkeleton } from "../../components/ui/Skeleton";
import { ErrorState } from "../../components/ui/ErrorState";

type HealthStatus = "healthy" | "degraded" | "blocked" | "insufficient_data" | "unknown";

const STATUS_COLORS: Record<HealthStatus, string> = {
  healthy: "text-green-700 bg-green-50 border-green-200",
  degraded: "text-yellow-700 bg-yellow-50 border-yellow-200",
  blocked: "text-red-700 bg-red-50 border-red-200",
  insufficient_data: "text-gray-700 bg-gray-50 border-gray-200",
  unknown: "text-gray-700 bg-gray-50 border-gray-200",
};

export function AdminIntelligencePage() {
  const qc = useQueryClient();
  const { data: health, isLoading: healthLoading, isError: healthError, error: healthErr } = useQuery({
    queryKey: ["intelligence-health"],
    queryFn: () => adminApi.evaluation.getIntelligenceHealth(),
  });

  const { data: runs, isLoading: runsLoading } = useQuery({
    queryKey: ["intelligence-runs"],
    queryFn: () => adminApi.evaluation.listRuns({ limit: 20 }),
  });

  const { data: snapshots, isLoading: snapshotsLoading } = useQuery({
    queryKey: ["intelligence-snapshots"],
    queryFn: () => adminApi.evaluation.listSnapshots({ limit: 30 }),
  });

  const { data: gateResults, isLoading: gatesLoading } = useQuery({
    queryKey: ["intelligence-gate-results"],
    queryFn: () => adminApi.evaluation.listGateResults({ limit: 50 }),
  });

  const { data: alerts, isLoading: alertsLoading } = useQuery({
    queryKey: ["intelligence-alerts"],
    queryFn: () => adminApi.evaluation.listAlerts({ limit: 50 }),
  });

  const { data: _gateDefinitions } = useQuery({
    queryKey: ["intelligence-gate-definitions"],
    queryFn: () => adminApi.evaluation.listGateDefinitions(),
  });

  const evaluationMutation = useMutation({
    mutationFn: (params: { evaluation_type: string; scope: string }) =>
      adminApi.evaluation.trigger(params.evaluation_type, params.scope),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["intelligence-runs"] });
      qc.invalidateQueries({ queryKey: ["intelligence-snapshots"] });
      qc.invalidateQueries({ queryKey: ["intelligence-health"] });
      qc.invalidateQueries({ queryKey: ["intelligence-gate-results"] });
      qc.invalidateQueries({ queryKey: ["intelligence-alerts"] });
    },
  });

  const gateEvaluationMutation = useMutation({
    mutationFn: () => adminApi.evaluation.triggerGateEvaluation(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["intelligence-gate-results"] });
      qc.invalidateQueries({ queryKey: ["intelligence-alerts"] });
      qc.invalidateQueries({ queryKey: ["intelligence-health"] });
    },
  });

  const resolveAlertMutation = useMutation({
    mutationFn: (alertId: string) => adminApi.evaluation.resolveAlert(alertId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["intelligence-alerts"] });
    },
  });

  const overallStatus = (health?.overall_status as HealthStatus) || "unknown";

  return (
    <>
      <Seo title="Intelligence Operations" noindex />
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Intelligence Operations</h1>
        <p className="mt-1 text-slate-600">M94 quality gates, health, and operational alerts.</p>

        {healthError && (
          <div className="mt-6">
            <ErrorState message={healthErr?.message ?? "Failed to load health."} retry={() => void qc.invalidateQueries({ queryKey: ["intelligence-health"] })} />
          </div>
        )}

        {healthLoading ? (
          <div className="mt-8"><ListSkeleton rows={1} /></div>
        ) : health ? (
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card>
              <p className="text-sm font-medium text-slate-500">Overall Status</p>
              <p className={`mt-1 inline-flex rounded-md border px-2 py-1 text-sm font-semibold ${STATUS_COLORS[overallStatus] || STATUS_COLORS.unknown}`}>{overallStatus}</p>
            </Card>
            <Card>
              <p className="text-sm font-medium text-slate-500">Components</p>
              <p className="mt-1 text-3xl font-bold text-slate-900">{health.components?.length ?? 0}</p>
            </Card>
            <Card>
              <p className="text-sm font-medium text-slate-500">Active Alerts</p>
              <p className="mt-1 text-3xl font-bold text-slate-900">{alerts?.items?.filter((a: any) => !a.resolved).length ?? 0}</p>
            </Card>
            <Card>
              <p className="text-sm font-medium text-slate-500">Generated At</p>
              <p className="mt-1 text-sm text-slate-700">{health.generated_at ? new Date(health.generated_at).toLocaleString() : "—"}</p>
            </Card>
          </div>
        ) : null}

        {health?.warnings?.length ? (
          <div className="mt-4 rounded-md border border-yellow-300 bg-yellow-50 p-4">
            <h3 className="font-semibold text-yellow-800">Warnings</h3>
            <ul className="mt-2 list-disc pl-5 text-sm text-yellow-700">
              {health.warnings.map((w: string) => (<li key={w}>{w}</li>))}
            </ul>
          </div>
        ) : null}

        <div className="mt-10 flex gap-3">
          <button
            onClick={() => evaluationMutation.mutate({ evaluation_type: "manual", scope: "global" })}
            disabled={evaluationMutation.isPending}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
          >
            {evaluationMutation.isPending ? "Running..." : "Run Evaluation"}
          </button>
          <button
            onClick={() => gateEvaluationMutation.mutate()}
            disabled={gateEvaluationMutation.isPending}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
          >
            {gateEvaluationMutation.isPending ? "Evaluating..." : "Evaluate Gates"}
          </button>
        </div>

        <div className="mt-10 grid gap-6 lg:grid-cols-2">
          <Card>
            <h2 className="text-lg font-semibold text-slate-900">Component Health</h2>
            <div className="mt-4 flex flex-col gap-3">
              {healthLoading ? (
                <ListSkeleton rows={3} />
              ) : health?.components?.length ? (
                health.components.map((c: any) => (
                  <div key={c.component} className="flex items-center justify-between text-sm">
                    <span className="truncate text-slate-700">{c.component}</span>
                    <span className={`shrink-0 rounded-md border px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[c.status as HealthStatus] || STATUS_COLORS.unknown}`}>{c.status}</span>
                  </div>
                ))
              ) : (
                <p className="text-sm text-slate-500">No component health data yet.</p>
              )}
            </div>
          </Card>

          <Card>
            <h2 className="text-lg font-semibold text-slate-900">Quality Gate Results</h2>
            <div className="mt-4 flex flex-col gap-3">
              {gatesLoading ? (
                <ListSkeleton rows={3} />
              ) : gateResults?.items?.length ? (
                gateResults.items.map((g: any) => (
                  <div key={g.gate_id} className="flex items-center justify-between text-sm">
                    <span className="truncate text-slate-700">{g.gate_id}</span>
                    <span className={`shrink-0 rounded-md border px-2 py-0.5 text-xs font-medium ${g.result === "pass" ? "text-green-700 bg-green-50 border-green-200" : g.result === "fail" ? "text-red-700 bg-red-50 border-red-200" : "text-yellow-700 bg-yellow-50 border-yellow-200"}`}>{g.result}</span>
                  </div>
                ))
              ) : (
                <p className="text-sm text-slate-500">No gate results yet.</p>
              )}
            </div>
          </Card>
        </div>

        <div className="mt-10 grid gap-6 lg:grid-cols-2">
          <Card>
            <h2 className="text-lg font-semibold text-slate-900">Recent Evaluation Runs</h2>
            <div className="mt-4 flex flex-col gap-3">
              {runsLoading ? (
                <ListSkeleton rows={3} />
              ) : runs?.items.map((r: any) => (
                <div key={r.run_id} className="flex items-center justify-between text-sm">
                  <span className="truncate text-slate-700">{r.run_id}</span>
                  <span className="shrink-0 text-slate-500">{r.status}</span>
                </div>
              ))}
              {!runs?.items.length && (<p className="text-sm text-slate-500">No evaluation runs yet.</p>)}
            </div>
          </Card>

          <Card>
            <h2 className="text-lg font-semibold text-slate-900">Quality Snapshots</h2>
            <div className="mt-4 flex flex-col gap-3">
              {snapshotsLoading ? (
                <ListSkeleton rows={3} />
              ) : snapshots?.items.map((s: any) => (
                <div key={s.snapshot_id} className="flex items-center justify-between text-sm">
                  <span className="truncate text-slate-700">{s.snapshot_id}</span>
                  <span className="shrink-0 text-slate-500">{s.overall_quality?.toFixed(2) ?? "—"}</span>
                </div>
              ))}
              {!snapshots?.items.length && (<p className="text-sm text-slate-500">No snapshots yet.</p>)}
            </div>
          </Card>
        </div>

        <div className="mt-10">
          <Card>
            <h2 className="text-lg font-semibold text-slate-900">Operational Alerts</h2>
            <div className="mt-4 flex flex-col gap-3">
              {alertsLoading ? (
                <ListSkeleton rows={3} />
              ) : alerts?.items?.length ? (
                alerts.items.map((a: any) => (
                  <div key={a.alert_id} className="flex items-center justify-between text-sm">
                    <div className="flex-1">
                      <span className="truncate text-slate-700">{a.message}</span>
                      <span className="ml-2 text-xs text-slate-500">{a.component}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`shrink-0 rounded-md border px-2 py-0.5 text-xs font-medium ${a.resolved ? "text-gray-700 bg-gray-50 border-gray-200" : a.severity === "critical" ? "text-red-700 bg-red-50 border-red-200" : a.severity === "warning" ? "text-yellow-700 bg-yellow-50 border-yellow-200" : "text-blue-700 bg-blue-50 border-blue-200"}`}>{a.severity}</span>
                      {!a.resolved && (
                        <button
                          onClick={() => resolveAlertMutation.mutate(a.alert_id)}
                          disabled={resolveAlertMutation.isPending}
                          className="rounded-md border border-slate-300 px-2 py-0.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                        >
                          Resolve
                        </button>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-slate-500">No operational alerts.</p>
              )}
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}
