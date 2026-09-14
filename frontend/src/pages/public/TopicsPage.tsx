import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Seo } from "../../components/Seo";
import { publicApi } from "../../api";
import { Card } from "../../components/ui/Card";
import { ListSkeleton } from "../../components/ui/Skeleton";
import { ErrorState } from "../../components/ui/ErrorState";
import { EmptyState } from "../../components/ui/EmptyState";
import type { Topic } from "../../types";

export function TopicsPage() {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["topics"],
    queryFn: () => publicApi.topics(),
  });

  return (
    <>
      <Seo
        title="Topics"
        description="Browse news articles organized by topic."
        canonical="/topics"
      />
      <div className="container-page py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900">Topics</h1>
          <p className="mt-1 text-slate-600">
            Browse articles organized by topic.
          </p>
        </div>

        {isError && (
          <ErrorState
            message={error?.message ?? "Failed to load topics."}
            retry={() => void refetch()}
          />
        )}

        {isLoading ? (
          <ListSkeleton rows={3} />
        ) : data && data.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.map((topic: Topic) => (
              <Card key={topic.id} as="article" className="transition-shadow hover:shadow-md">
                <h2 className="text-lg font-semibold text-slate-900">
                  <Link
                    to={`/news?topic=${topic.id}`}
                    className="hover:text-brand-700"
                  >
                    {topic.name}
                  </Link>
                </h2>
                {topic.description && (
                  <p className="mt-1 text-sm text-slate-600">{topic.description}</p>
                )}
                <p className="mt-2 text-sm text-slate-500">
                  {topic.article_count} article{topic.article_count === 1 ? "" : "s"}
                </p>
                <Link
                  to={`/news?topic=${topic.id}`}
                  className="mt-2 inline-block text-sm font-medium text-brand-600 hover:underline"
                >
                  Browse articles &rarr;
                </Link>
              </Card>
            ))}
          </div>
        ) : (
          <EmptyState title="No topics" description="Topics will appear here once extracted from articles." />
        )}
      </div>
    </>
  );
}
