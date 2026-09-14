import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Seo } from "../../components/Seo";
import { publicApi } from "../../api";
import { Card } from "../../components/ui/Card";
import { ListSkeleton } from "../../components/ui/Skeleton";
import { ErrorState } from "../../components/ui/ErrorState";
import { EmptyState } from "../../components/ui/EmptyState";
import type { Company } from "../../types";

export function CompaniesPage() {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["companies"],
    queryFn: () => publicApi.companies(),
  });

  return (
    <>
      <Seo
        title="Companies"
        description="Browse news articles organized by company."
        canonical="/companies"
      />
      <div className="container-page py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900">Companies</h1>
          <p className="mt-1 text-slate-600">
            Browse articles mentioning specific companies.
          </p>
        </div>

        {isError && (
          <ErrorState
            message={error?.message ?? "Failed to load companies."}
            retry={() => void refetch()}
          />
        )}

        {isLoading ? (
          <ListSkeleton rows={3} />
        ) : data && data.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.map((company: Company) => (
              <Card key={company.id} as="article" className="transition-shadow hover:shadow-md">
                <h2 className="text-lg font-semibold text-slate-900">
                  <Link
                    to={`/news?company=${company.id}`}
                    className="hover:text-brand-700"
                  >
                    {company.name}
                  </Link>
                </h2>
                {company.description && (
                  <p className="mt-1 text-sm text-slate-600">{company.description}</p>
                )}
                <p className="mt-2 text-sm text-slate-500">
                  {company.article_count} article{company.article_count === 1 ? "" : "s"}
                </p>
                <Link
                  to={`/news?company=${company.id}`}
                  className="mt-2 inline-block text-sm font-medium text-brand-600 hover:underline"
                >
                  Browse articles &rarr;
                </Link>
              </Card>
            ))}
          </div>
        ) : (
          <EmptyState title="No companies" description="Companies will appear here once extracted from articles." />
        )}
      </div>
    </>
  );
}
