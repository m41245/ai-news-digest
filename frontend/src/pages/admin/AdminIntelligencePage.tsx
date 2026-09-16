import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Seo } from "../../components/Seo";
import { Card } from "../../components/ui/Card";
import { adminApi } from "../../api";
import { ListSkeleton } from "../../components/ui/Skeleton";
import { ErrorState } from "../../components/ui/ErrorState";

export function AdminIntelligencePage() {
  const qc = useQueryClient();
  const { data: health, isLoading: healthLoading, isError: healthError, error: healthErr } = useQuery({
    queryKey: ["intelligence-health"],
    queryFn: () => adminApi.evaluation.getHealth(),
  });

  const { data: runs, isLoading: runsLoading } = useQuery({
    queryKey: ["intelligence-runs"],
    queryFn: () => adminApi.evaluation.listRuns({ limit: 20 }),
  });

  const { data: snapshots, isLoading: snapshotsLoading } = useQuery({
    queryKey: ["intelligence-snapshots"],
    queryFn: () => adminApi.evaluation.listSnapshots({ limit: 30 }),
  });

  const triggerMutation = useMutation({
    mutationFn: (params: { evaluation_type: string; scope: string }) =>
      adminApi.evaluation.trigger(params.evaluation_type, params.scope),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["intelligence-runs"] });
      qc.invalidateQueries({ queryKey: ["intelligence-snapshots"] });
      qc.invalidateQueries({ queryKey: ["intelligence-health"] });
    },
  });

  return (
    <>
      <Seo title="Intelligence Quality" noindex />
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Intelligence Quality</h1>
        <p className="mt-1 text-slate-600">M93 evaluation and drift monitoring.</p>

        {healthError && (
          <div className="mt-6">
            <ErrorState message={healthErr?.message ?? "Failed to load health."} retry={() => void qc.invalidateQueries({ queryKey: ["intelligence-health"] })} />
          </div>
        )}

        {healthLoading ? (
          <div className="mt-8"><ListSkeleton rows={1} /></div>
        ) : health ? (
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Status" value={health.status} />
            <StatCard label="Overall Quality" value={health.overall_quality?.toFixed(2) ?? "—"} />
            <StatCard label="Sample Count" value={health.sample_count} />
            <StatCard label="Evaluated At" value={health.evaluated_at ? new Date(health.evaluated_at).toLocaleString() : "—"} />
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
            onClick={() => triggerMutation.mutate({ evaluation_type: "manual", scope: "global" })}
            disabled={triggerMutation.isPending}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
          >
            {triggerMutation.isPending ? "Running..." : "Run Evaluation"}
          </button>
        </div>

        <div className="mt-10 grid gap-6 lg:grid-cols-2">
          <Card>
            <h2 className="text-lg font-semibold text-slate-900">Recent Evaluation Runs</h2>
            <div className="mt-4 flex flex-col gap-3">
              {runsLoading ? (
                <ListSkeleton rows={3} />
              ) : runs?.items.map((r) => (
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
              ) : snapshots?.items.map((s) => (
                <div key={s.snapshot_id} className="flex items-center justify-between text-sm">
                  <span className="truncate text-slate-700">{s.snapshot_id}</span>
                  <span className="shrink-0 text-slate-500">{s.overall_quality?.toFixed(2) ?? "—"}</span>
                </div>
              ))}
              {!snapshots?.items.length && (<p className="text-sm text-slate-500">No snapshots yet.</p>)}
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <Card>
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-1 text-3xl font-bold text-slate-900">{String(value)}</p>
    </Card>
  );
}
