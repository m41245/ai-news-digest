import { useEffect, useState } from "react";
import { publicApi } from "../../api";
import type { PublicTrendSearch } from "../../types";
import { TrendCard } from "../../components/TrendCard";
import { Pagination } from "../../components/ui/Pagination";
import { EmptyState } from "../../components/ui/EmptyState";
import { Skeleton } from "../../components/ui/Skeleton";

const DEFAULT_LIMIT = 20;

export function TrendsPage() {
  const [trends, setTrends] = useState<PublicTrendSearch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [trendType, setTrendType] = useState<string>("");
  const [status, setStatus] = useState<string>("");

  const loadTrends = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await publicApi.trends({
        limit: DEFAULT_LIMIT,
        offset,
        trend_type: trendType || undefined,
        status: status || undefined,
      });
      setTrends(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load trends");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadTrends();
  }, [offset, trendType, status]);

  const currentPage = Math.floor(offset / DEFAULT_LIMIT) + 1;
  const totalPages = Math.max(1, Math.ceil(total / DEFAULT_LIMIT));

  const handlePageChange = (page: number) => {
    setOffset((page - 1) * DEFAULT_LIMIT);
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Trending</h1>
        <p className="mt-2 text-gray-600">
          Emerging and rising topics, companies, categories, and stories across AI news.
        </p>
      </div>

      <div className="mb-6 flex flex-wrap gap-4">
        <select
          value={trendType}
          onChange={(e) => {
            setTrendType(e.target.value);
            setOffset(0);
          }}
          className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm"
        >
          <option value="">All types</option>
          <option value="topic_trend">Topics</option>
          <option value="company_trend">Companies</option>
          <option value="category_trend">Categories</option>
          <option value="story_trend">Stories</option>
        </select>
        <select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setOffset(0);
          }}
          className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm"
        >
          <option value="">All statuses</option>
          <option value="emerging">Emerging</option>
          <option value="rising">Rising</option>
          <option value="sustained">Sustained</option>
          <option value="cooling">Cooling</option>
          <option value="stale">Stale</option>
        </select>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-4 text-red-700">{error}</div>
      )}

      {loading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-48" />
          ))}
        </div>
      ) : trends.length === 0 ? (
        <EmptyState
          title="No trends found"
          description="Trends will appear here as activity is detected across the platform."
        />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {trends.map((trend) => (
              <TrendCard key={trend.id} trend={trend} />
            ))}
          </div>
          <div className="mt-8">
            <Pagination
              page={currentPage}
              totalPages={totalPages}
              onChange={handlePageChange}
            />
          </div>
        </>
      )}
    </div>
  );
}
