import { Link } from "react-router-dom";
import { Card } from "./ui/Card";
import { Badge } from "./ui/Badge";

interface TopStoryCardProps {
  story: {
    cluster_id: string;
    title: string;
    slug: string;
    summary?: string | null;
    importance_score?: number | null;
    confidence?: number | null;
    ranking_score?: number | null;
    ranking_explanation?: string | null;
  };
  digestId?: string;
}

export function TopStoryCard({ story, digestId }: TopStoryCardProps) {
  return (
    <Card as="article" className="border-brand-200 bg-brand-50/50">
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <Badge tone="brand">Top Story</Badge>
          {digestId && (
            <Link
              to={`/digests/${digestId}`}
              className="text-xs font-medium text-brand-600 hover:underline"
            >
              View digest
            </Link>
          )}
        </div>
        <h2 className="text-xl font-semibold text-slate-900">
          <Link
            to={`/stories/${story.slug}`}
            className="hover:text-brand-700 focus-visible:text-brand-700"
          >
            {story.title}
          </Link>
        </h2>
        {story.summary && (
          <p className="prose-body text-sm text-slate-700">{story.summary}</p>
        )}
        <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
          {story.importance_score != null && (
            <span>Importance: {story.importance_score.toFixed(2)}</span>
          )}
          {story.confidence != null && (
            <span>Confidence: {story.confidence.toFixed(2)}</span>
          )}
          {story.ranking_score != null && (
            <span>Rank: {story.ranking_score.toFixed(2)}</span>
          )}
        </div>
      </div>
    </Card>
  );
}
