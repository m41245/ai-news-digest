import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Seo } from "../../components/Seo";
import { publicApi } from "../../api";
import { Card } from "../../components/ui/Card";
import { ListSkeleton } from "../../components/ui/Skeleton";
import { ErrorState } from "../../components/ui/ErrorState";
import { EmptyState } from "../../components/ui/EmptyState";
import type { Category } from "../../types";

export function CategoriesPage() {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["categories"],
    queryFn: () => publicApi.categories(),
  });

  return (
    <>
      <Seo
        title="Categories"
        description="Browse news articles organized by category."
      />
      <div className="container-page py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900">Categories</h1>
          <p className="mt-1 text-slate-600">
            Browse articles organized by topic.
          </p>
        </div>

        {isError && (
          <ErrorState
            message={error?.message ?? "Failed to load categories."}
            retry={() => void refetch()}
          />
        )}

        {isLoading ? (
          <ListSkeleton rows={3} />
        ) : data && data.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.map((category: Category) => (
              <Card key={category.id} as="article" className="transition-shadow hover:shadow-md">
                <h2 className="text-lg font-semibold text-slate-900">
                  <Link
                    to={`/news?category=${category.id}`}
                    className="hover:text-brand-700"
                  >
                    {category.name}
                  </Link>
                </h2>
                {category.description && (
                  <p className="mt-1 text-sm text-slate-600">{category.description}</p>
                )}
                <Link
                  to={`/news?category=${category.id}`}
                  className="mt-2 inline-block text-sm font-medium text-brand-600 hover:underline"
                >
                  Browse articles &rarr;
                </Link>
              </Card>
            ))}
          </div>
        ) : (
          <EmptyState title="No categories" description="Categories will appear here once created." />
        )}
      </div>
    </>
  );
}
