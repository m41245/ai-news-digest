import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Seo } from "../../components/Seo";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { adminApi } from "../../api";

interface TaskResult {
  message?: string;
  error?: string;
}

export function AdminOperationsPage() {
  const [results, setResults] = useState<Record<string, TaskResult>>({});

  const { data: pipeline } = useQuery({
    queryKey: ["pipeline-status"],
    queryFn: () => adminApi.pipelineStatus(),
    refetchInterval: 60_000,
  });

  const ingestion = useMutation({
    mutationFn: () => adminApi.triggerIngestion(),
    onSuccess: (r) => setResults((s) => ({ ...s, ingestion: { message: r.message } })),
    onError: (e: Error) => setResults((s) => ({ ...s, ingestion: { error: e.message } })),
  });

  const digest = useMutation({
    mutationFn: () => adminApi.triggerDigest(),
    onSuccess: (r) => setResults((s) => ({ ...s, digest: { message: r.message } })),
    onError: (e: Error) => setResults((s) => ({ ...s, digest: { error: e.message } })),
  });

  const cleanup = useMutation({
    mutationFn: () => adminApi.triggerCleanup(),
    onSuccess: (r) => setResults((s) => ({ ...s, cleanup: { message: r.message } })),
    onError: (e: Error) => setResults((s) => ({ ...s, cleanup: { error: e.message } })),
  });

  const pipelineStatus = pipeline?.status ?? "unknown";
  const pipelineWarnings = pipeline?.warnings ?? [];

  return (
    <>
      <Seo title="Operations" noindex />
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Operations</h1>
        <p className="mt-1 text-slate-600">Trigger pipeline tasks and monitor status.</p>

        {pipelineWarnings.length > 0 && (
          <div className="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-4">
            <h3 className="text-sm font-medium text-amber-800">Warnings</h3>
            <ul className="mt-2 list-disc pl-5 text-sm text-amber-700">
              {pipelineWarnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="mt-8 grid gap-6 lg:grid-cols-2">
          <Card>
            <h2 className="text-lg font-semibold text-slate-900">Pipeline tasks</h2>
            <p className="mt-1 text-sm text-slate-600">
              Trigger background tasks via Celery.
            </p>
            <div className="mt-4 flex flex-col gap-3">
              <OperationRow
                label="Ingest sources"
                description="Fetch new articles from all active RSS sources."
                result={results.ingestion}
                loading={ingestion.isPending}
                onRun={() => ingestion.mutate()}
              />
              <OperationRow
                label="Generate digest"
                description="Generate a daily digest from eligible articles."
                result={results.digest}
                loading={digest.isPending}
                onRun={() => digest.mutate()}
              />
              <OperationRow
                label="Cleanup"
                description="Remove old articles (30+ days)."
                result={results.cleanup}
                loading={cleanup.isPending}
                onRun={() => cleanup.mutate()}
              />
            </div>
          </Card>

          <Card>
            <h2 className="text-lg font-semibold text-slate-900">Pipeline status</h2>
            <p className="mt-1 text-sm text-slate-600">
              Latest observed pipeline events.
            </p>
            <dl className="mt-4 flex flex-col gap-3 text-sm">
              <PipelineRow
                label="Ingestion"
                timestamp={pipeline?.ingestion?.last_attempt}
                status={pipelineStatus}
              />
              <PipelineRow
                label="Processing"
                timestamp={pipeline?.processing?.last_attempt}
                status={pipelineStatus}
              />
              <PipelineRow
                label="Digest"
                timestamp={pipeline?.digest?.last_attempt}
                status={pipelineStatus}
              />
              <PipelineRow
                label="Delivery"
                timestamp={pipeline?.delivery?.last_attempt}
                status={pipelineStatus}
              />
            </dl>
            {(pipeline?.counts?.new_articles ?? 0) > 0 && (
              <p className="mt-3 text-sm text-amber-600">
                {pipeline?.counts?.new_articles} pending article(s) awaiting processing
              </p>
            )}
            {(pipeline?.counts?.failed_deliveries ?? 0) > 0 && (
              <p className="mt-1 text-sm text-red-600">
                {pipeline?.counts?.failed_deliveries} failed delivery(s)
              </p>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}

interface OperationRowProps {
  label: string;
  description: string;
  loading: boolean;
  result?: TaskResult;
  onRun: () => void;
}

function OperationRow({ label, description, loading, result, onRun }: OperationRowProps) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-lg border border-slate-200 p-4">
      <div>
        <p className="text-sm font-medium text-slate-900">{label}</p>
        <p className="text-xs text-slate-500">{description}</p>
        {result?.message && (
          <p className="mt-1 text-xs text-emerald-600">{result.message}</p>
        )}
        {result?.error && (
          <p className="mt-1 text-xs text-red-600">{result.error}</p>
        )}
      </div>
      <Button variant="secondary" size="sm" disabled={loading} onClick={onRun}>
        {loading ? "Running…" : "Run"}
      </Button>
    </div>
  );
}

interface PipelineRowProps {
  label: string;
  timestamp: string | null | undefined;
  status: string | undefined;
}

function PipelineRow({ label, timestamp, status }: PipelineRowProps) {
  const tone = status === "ok" ? "text-emerald-600" : "text-amber-600";
  return (
    <div className="flex justify-between">
      <dt className="text-slate-500">{label}</dt>
      <dd className={`font-medium ${tone}`}>
        {timestamp ? new Date(timestamp).toLocaleString() : "—"}
      </dd>
    </div>
  );
}
