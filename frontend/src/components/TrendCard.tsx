import type { PublicTrendSearch } from "../types";

const STATUS_COLORS: Record<string, string> = {
  emerging: "bg-purple-100 text-purple-800",
  rising: "bg-blue-100 text-blue-800",
  sustained: "bg-green-100 text-green-800",
  cooling: "bg-yellow-100 text-yellow-800",
  stale: "bg-gray-100 text-gray-800",
};

const TYPE_LABELS: Record<string, string> = {
  topic_trend: "Topic",
  company_trend: "Company",
  category_trend: "Category",
  story_trend: "Story",
  emerging_trend: "Emerging",
};

export function TrendCard({ trend }: { trend: PublicTrendSearch }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium uppercase tracking-wide text-gray-500">
              {TYPE_LABELS[trend.trend_type] || trend.trend_type}
            </span>
            <span
              className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                STATUS_COLORS[trend.status] || STATUS_COLORS.stale
              }`}
            >
              {trend.status}
            </span>
          </div>
          <h3 className="mt-2 text-lg font-semibold text-gray-900">
            {trend.display_name}
          </h3>
          <p className="mt-1 text-sm text-gray-600">{trend.explanation}</p>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-gray-500">Trend score</span>
          <p className="font-medium text-gray-900">{trend.trend_score.toFixed(1)}</p>
        </div>
        <div>
          <span className="text-gray-500">Momentum</span>
          <p className="font-medium text-gray-900">{trend.momentum_score.toFixed(1)}</p>
        </div>
        <div>
          <span className="text-gray-500">Recent activity</span>
          <p className="font-medium text-gray-900">{trend.recent_activity} articles</p>
        </div>
        <div>
          <span className="text-gray-500">Sources</span>
          <p className="font-medium text-gray-900">{trend.source_count}</p>
        </div>
      </div>
      <div className="mt-4 text-xs text-gray-400">
        Last detected: {trend.last_detected_at ? new Date(trend.last_detected_at).toLocaleString() : "N/A"}
      </div>
    </div>
  );
}
