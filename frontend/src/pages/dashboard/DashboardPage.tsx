import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../../auth/AuthContext";
import { Seo } from "../../components/Seo";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { publicApi } from "../../api";
import { ArticleCard } from "../../components/ArticleCard";
import { ListSkeleton } from "../../components/ui/Skeleton";
import { ErrorState } from "../../components/ui/ErrorState";
import { formatDateTime } from "../../utils";

export function DashboardPage() {
  const { user } = useAuth();

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["dashboard-articles"],
    queryFn: () => publicApi.articles({ limit: 6 }),
  });

  return (
    <>
      <Seo title="Dashboard" noindex />
      <div className="container-page py-8">
        <div className="mb-8 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Dashboard</h1>
            <p className="mt-1 text-slate-600">
              Welcome back{user?.email ? `, ${user.email}` : ""}.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="secondary">
              <Link to="/news" className="inline-flex">
                Browse all news
              </Link>
            </Button>
            <Button>
              <Link to="/digests" className="inline-flex">
                View digests
              </Link>
            </Button>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-1">
            <h2 className="text-lg font-semibold text-slate-900">Your account</h2>
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
                <dt className="text-slate-500">Member since</dt>
                <dd className="font-medium text-slate-900">
                  {formatDateTime(user?.created_at)}
                </dd>
              </div>
            </dl>
          </Card>

          <div className="lg:col-span-2">
            <h2 className="mb-4 text-lg font-semibold text-slate-900">
              Latest articles
            </h2>
            {isError && (
              <ErrorState
                message={error?.message ?? "Failed to load articles."}
                retry={() => void refetch()}
              />
            )}
            {isLoading ? (
              <ListSkeleton rows={3} />
            ) : data && data.items.length > 0 ? (
              <div className="grid gap-4 sm:grid-cols-2">
                {data.items.map((article) => (
                  <ArticleCard key={article.id} article={article} />
                ))}
              </div>
            ) : (
              <Card>
                <p className="text-sm text-slate-600">
                  No articles yet. They will appear here once ingestion runs.
                </p>
              </Card>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
