import { Link } from "react-router-dom";
import { Card } from "./ui/Card";
import { Badge } from "./ui/Badge";

interface StoryCardProps {
  story: {
    cluster_id?: string | null;
    headline?: string | null;
    summary?: string | null;
    key_takeaways: string[];
    why_it_matters?: string | null;
    activity_status?: string | null;
  };
  index: number;
  digestId?: string;
}

export function StoryCard({ story, index, digestId }: StoryCardProps) {
  const headline = story.headline || `Story ${index + 1}`;
  const isTopStory = index === 0 && story.cluster_id;

  return (
    <Card as="article" className={isTopStory ? "border-brand-200 bg-brand-50/30" : ""}>
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          {isTopStory && <Badge tone="brand">Top Story</Badge>}
          {story.activity_status && (
            <Badge tone={story.activity_status === "breaking" ? "danger" : story.activity_status === "developing" ? "warning" : "neutral"}>
              {story.activity_status}
            </Badge>
          )}
          {story.cluster_id && (
            <Link
              to={`/stories/${story.cluster_id}`}
              className="text-xs font-medium text-brand-600 hover:underline"
            >
              View full story
            </Link>
          )}
          {digestId && (
            <Link
              to={`/digests/${digestId}`}
              className="ml-auto text-xs text-slate-500 hover:underline"
            >
              Digest
            </Link>
          )}
        </div>
        <h3 className="text-lg font-semibold text-slate-900">{headline}</h3>
        {story.summary && (
          <p className="prose-body text-sm text-slate-700">{story.summary}</p>
        )}
        {story.key_takeaways && story.key_takeaways.length > 0 && (
          <ul className="list-inside list-disc text-sm text-slate-600">
            {story.key_takeaways.slice(0, 3).map((takeaway, i) => (
              <li key={i}>{takeaway}</li>
            ))}
          </ul>
        )}
        {story.why_it_matters && (
          <p className="text-sm text-slate-600">
            <span className="font-semibold">Why it matters:</span> {story.why_it_matters}
          </p>
        )}
      </div>
    </Card>
  );
}
