import { Link } from "react-router-dom";
import type { PublicDigest } from "../types";
import { Card } from "./ui/Card";
import { Badge } from "./ui/Badge";
import { formatDate } from "../utils";

interface DigestCardProps {
  digest: PublicDigest;
}

export function DigestCard({ digest }: DigestCardProps) {
  return (
    <Card as="article" className="transition-shadow hover:shadow-md">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <Badge tone="success">{digest.format.toLowerCase()}</Badge>
          <span className="ml-auto text-xs text-slate-500">
            {formatDate(digest.generated_at)}
          </span>
        </div>
        <h2 className="text-lg font-semibold text-slate-900">
          <Link
            to={`/digests/${digest.id}`}
            className="hover:text-brand-700 focus-visible:text-brand-700"
          >
            {digest.title}
          </Link>
        </h2>
        <p className="prose-body text-sm">
          {digest.article_count} article
          {digest.article_count === 1 ? "" : "s"}
        </p>
      </div>
    </Card>
  );
}
