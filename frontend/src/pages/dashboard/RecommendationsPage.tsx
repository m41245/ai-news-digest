import { useEffect, useState } from "react";
import { personalizedApi } from "../../api";
import type { RecommendationItemResponse } from "../../types";

export function RecommendationsPage() {
  const [recommendations, setRecommendations] = useState<RecommendationItemResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await personalizedApi.recommendations({ page: 1, page_size: 20 });
        if (!cancelled) {
          setRecommendations(data.items);
        }
      } catch {
        if (!cancelled) setError("Failed to load recommendations.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) return <div className="p-6">Loading recommendations...</div>;
  if (error) return <div className="p-6 text-red-600">{error}</div>;

  const stories = recommendations.filter((r) => r.item_type === "story");
  const trends = recommendations.filter((r) => r.item_type === "trend");

  return (
    <div className="mx-auto max-w-4xl p-6">
      <h1 className="mb-6 text-2xl font-bold">Recommended For You</h1>

      {recommendations.length === 0 ? (
        <p className="text-gray-500">
          No recommendations yet. Follow some companies, topics, or categories to see personalized content.
        </p>
      ) : (
        <div className="grid gap-4">
          {recommendations.map((item) => (
            <div key={item.id} className="rounded border p-4">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <h3 className="text-lg font-semibold">{item.title}</h3>
                <span className="rounded bg-blue-100 px-2 py-0.5 text-sm text-blue-800">
                  Score: {item.recommendation_score.toFixed(1)}
                </span>
                {item.item_type === "story" && (
                  <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">Story</span>
                )}
                {item.item_type === "trend" && (
                  <span className="rounded bg-purple-100 px-2 py-0.5 text-xs text-purple-600">Trend</span>
                )}
              </div>

              {item.summary && (
                <p className="mb-2 text-sm text-gray-700">{item.summary}</p>
              )}

              <div className="mb-2 flex flex-wrap gap-2 text-sm text-gray-600">
                {item.source_name && <span>{item.source_name}</span>}
                {item.published_at && (
                  <span>{new Date(item.published_at).toLocaleDateString()}</span>
                )}
                {item.importance_score != null && (
                  <span className="rounded bg-green-100 px-2 py-0.5 text-green-800">
                    Importance: {(item.importance_score * 100).toFixed(0)}%
                  </span>
                )}
                {item.activity_status && (
                  <span className="rounded bg-yellow-100 px-2 py-0.5 text-yellow-800">
                    {item.activity_status}
                  </span>
                )}
                {item.trend_score != null && (
                  <span className="rounded bg-purple-100 px-2 py-0.5 text-purple-800">
                    Trend: {item.trend_score.toFixed(1)}
                  </span>
                )}
              </div>

              {item.companies.length > 0 && (
                <div className="mb-1 flex flex-wrap gap-1 text-xs text-gray-500">
                  {item.companies.map((company) => (
                    <span key={company} className="rounded bg-gray-100 px-2 py-0.5">{company}</span>
                  ))}
                </div>
              )}
              {item.topics.length > 0 && (
                <div className="mb-1 flex flex-wrap gap-1 text-xs text-gray-500">
                  {item.topics.map((topic) => (
                    <span key={topic} className="rounded bg-gray-100 px-2 py-0.5">{topic}</span>
                  ))}
                </div>
              )}
              {item.categories.length > 0 && (
                <div className="mb-2 flex flex-wrap gap-1 text-xs text-gray-500">
                  {item.categories.map((category) => (
                    <span key={category} className="rounded bg-gray-100 px-2 py-0.5">{category}</span>
                  ))}
                </div>
              )}

              {item.recommendation_reasons.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {item.recommendation_reasons.map((reason, idx) => (
                    <span key={idx} className="rounded bg-blue-50 px-2 py-0.5 text-xs text-blue-700">
                      {reason}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {stories.length > 0 && trends.length > 0 && (
        <div className="mt-8">
          <h2 className="mb-4 text-xl font-semibold">Trends You Might Like</h2>
          <div className="grid gap-4">
            {trends.map((trend) => (
              <div key={trend.id} className="rounded border p-4">
                <h3 className="mb-2 text-lg font-semibold">{trend.title}</h3>
                <div className="mb-2 flex flex-wrap gap-2 text-sm text-gray-600">
                  <span className="rounded bg-purple-100 px-2 py-0.5 text-purple-800">
                    Trend: {trend.trend_score?.toFixed(1)}
                  </span>
                  <span>Momentum: {trend.momentum_score?.toFixed(1)}</span>
                  <span className="rounded bg-blue-100 px-2 py-0.5 text-blue-800">
                    Score: {trend.recommendation_score.toFixed(1)}
                  </span>
                </div>
                {trend.recommendation_reasons.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {trend.recommendation_reasons.map((reason, idx) => (
                      <span key={idx} className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-700">
                        {reason}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
