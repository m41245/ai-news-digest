import { useEffect, useState } from "react";
import { personalizedApi } from "../../api";
import type { PersonalizedFeedItemResponse, PersonalizedTrendResponse } from "../../types";

export function PersonalizedFeedPage() {
  const [feed, setFeed] = useState<PersonalizedFeedItemResponse[]>([]);
  const [trends, setTrends] = useState<PersonalizedTrendResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"feed" | "trends">("feed");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [feedData, trendsData] = await Promise.all([
          personalizedApi.feed({ page: 1, page_size: 20 }),
          personalizedApi.trends({ page: 1, page_size: 10 }),
        ]);
        if (!cancelled) {
          setFeed(feedData.items);
          setTrends(trendsData);
        }
      } catch {
        if (!cancelled) setError("Failed to load personalized content.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) return <div className="p-6">Loading personalized content...</div>;
  if (error) return <div className="p-6 text-red-600">{error}</div>;

  return (
    <div className="mx-auto max-w-4xl p-6">
      <h1 className="mb-6 text-2xl font-bold">Personalized For You</h1>

      <div className="mb-4 flex gap-2 border-b">
        <button
          onClick={() => setActiveTab("feed")}
          className={`px-4 py-2 ${
            activeTab === "feed"
              ? "border-b-2 border-blue-600 font-semibold text-blue-600"
              : "text-gray-600 hover:text-gray-900"
          }`}
        >
          Stories ({feed.length})
        </button>
        <button
          onClick={() => setActiveTab("trends")}
          className={`px-4 py-2 ${
            activeTab === "trends"
              ? "border-b-2 border-blue-600 font-semibold text-blue-600"
              : "text-gray-600 hover:text-gray-900"
          }`}
        >
          Trends ({trends.length})
        </button>
      </div>

      {activeTab === "feed" && (
        <div>
          {feed.length === 0 ? (
            <p className="text-gray-500">No personalized stories yet. Follow some companies, topics, or categories to see relevant content.</p>
          ) : (
            <div className="grid gap-4">
              {feed.map((item) => (
                <div key={item.id} className="rounded border p-4">
                  <h3 className="mb-2 text-lg font-semibold">{item.title}</h3>
                  <div className="mb-2 flex flex-wrap gap-2 text-sm text-gray-600">
                    {item.source_name && <span>{item.source_name}</span>}
                    {item.published_at && (
                      <span>{new Date(item.published_at).toLocaleDateString()}</span>
                    )}
                    <span className="rounded bg-blue-100 px-2 py-0.5 text-blue-800">
                      Relevance: {item.relevance_score.toFixed(1)}
                    </span>
                  </div>
                  {item.relevance_reasons.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {item.relevance_reasons.map((reason, idx) => (
                        <span key={idx} className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-700">
                          {reason}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "trends" && (
        <div>
          {trends.length === 0 ? (
            <p className="text-gray-500">No personalized trends yet.</p>
          ) : (
            <div className="grid gap-4">
              {trends.map((trend) => (
                <div key={trend.id} className="rounded border p-4">
                  <h3 className="mb-2 text-lg font-semibold">{trend.display_name}</h3>
                  <div className="mb-2 flex flex-wrap gap-2 text-sm text-gray-600">
                    <span className="rounded bg-purple-100 px-2 py-0.5 text-purple-800">
                      {trend.trend_type}
                    </span>
                    <span>Score: {trend.trend_score.toFixed(1)}</span>
                    <span>Momentum: {trend.momentum_score.toFixed(1)}</span>
                    <span className="rounded bg-blue-100 px-2 py-0.5 text-blue-800">
                      Relevance: {trend.personalized_relevance_score.toFixed(1)}
                    </span>
                  </div>
                  {trend.relevance_reasons.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {trend.relevance_reasons.map((reason, idx) => (
                        <span key={idx} className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-700">
                          {reason}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
