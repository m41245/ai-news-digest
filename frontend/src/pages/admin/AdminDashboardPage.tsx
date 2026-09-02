import { useQuery } from "@tanstack/react-query";
import { Seo } from "../../components/Seo";
import { Card } from "../../components/ui/Card";
import { adminApi, publicApi } from "../../api";
import { ListSkeleton } from "../../components/ui/Skeleton";
import { ErrorState } from "../../components/ui/ErrorState";
import { formatDateTime } from "../../utils";

export function AdminDashboardPage() {
  const { data: stats, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["admin-stats"],
    queryFn: () => adminApi.stats(),
  });

  const { data: articles } = useQuery({
    queryKey: ["admin-recent-articles"],
    queryFn: () => publicApi.articles({ limit: 5 }),
  });

  const { data: digests } = useQuery({
    queryKey: ["admin-recent-digests"],
    queryFn: () => publicApi.digests({ limit: 5 }),
  });

  const { data: users } = useQuery({
    queryKey: ["admin-users"],
    queryFn: () => adminApi.users(),
  });

  return (
    <>
      <Seo title="Admin Dashboard" noindex />
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Admin Dashboard</h1>
        <p className="mt-1 text-slate-600">System overview and quick access.</p>

        {isError && (
          <div className="mt-6">
            <ErrorState
              message={error?.message ?? "Failed to load stats."}
              retry={() => void refetch()}
            />
          </div>
        )}

        {isLoading ? (
          <div className="mt-8">
            <ListSkeleton rows={1} />
          </div>
        ) : stats ? (
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Articles" value={stats.articles} />
            <StatCard label="Sources" value={stats.sources} />
            <StatCard label="Digests" value={stats.digests} />
            <StatCard label="Users" value={users?.total ?? 0} />
          </div>
        ) : null}

        <div className="mt-10 grid gap-6 lg:grid-cols-2">
          <Card>
            <h2 className="text-lg font-semibold text-slate-900">Recent articles</h2>
            <div className="mt-4 flex flex-col gap-3">
              {articles?.items.map((a) => (
                <div key={a.id} className="flex items-center justify-between text-sm">
                  <span className="truncate text-slate-700">{a.title}</span>
                  <span className="shrink-0 text-slate-500">
                    {formatDateTime(a.published_at)}
                  </span>
                </div>
              ))}
              {!articles?.items.length && (
                <p className="text-sm text-slate-500">No articles yet.</p>
              )}
            </div>
          </Card>
          <Card>
            <h2 className="text-lg font-semibold text-slate-900">Recent digests</h2>
            <div className="mt-4 flex flex-col gap-3">
              {digests?.items.map((d) => (
                <div key={d.id} className="flex items-center justify-between text-sm">
                  <span className="truncate text-slate-700">{d.title}</span>
                  <span className="shrink-0 text-slate-500">
                    {formatDateTime(d.generated_at)}
                  </span>
                </div>
              ))}
              {!digests?.items.length && (
                <p className="text-sm text-slate-500">No digests yet.</p>
              )}
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <Card>
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-1 text-3xl font-bold text-slate-900">{value}</p>
    </Card>
  );
}
