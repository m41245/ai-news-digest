import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Seo } from "../../components/Seo";
import { publicApi } from "../../api";
import { DigestCard } from "../../components/DigestCard";
import { ListSkeleton } from "../../components/ui/Skeleton";
import { ErrorState } from "../../components/ui/ErrorState";
import { EmptyState } from "../../components/ui/EmptyState";
import { Pagination } from "../../components/ui/Pagination";

const PAGE_SIZE = 12;

export function DigestsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Math.max(1, Number(searchParams.get("page") ?? "1"));

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["digests", page],
    queryFn: () => publicApi.digests({ limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }),
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <>
      <Seo
        title="Digests"
        description="Daily AI-generated news digests that summarize the most important articles."
      />
      <div className="container-page py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900">Digests</h1>
          <p className="mt-1 text-slate-600">
            Daily digests that collect and summarize the most important articles.
          </p>
        </div>

        {isError && (
          <ErrorState
            message={error?.message ?? "Failed to load digests."}
            retry={() => void refetch()}
          />
        )}

        {isLoading ? (
          <ListSkeleton rows={3} />
        ) : data && data.items.length > 0 ? (
          <>
            <p className="mb-4 text-sm text-slate-500">
              {data.total} digest{data.total === 1 ? "" : "s"}
            </p>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {data.items.map((digest) => (
                <DigestCard key={digest.id} digest={digest} />
              ))}
            </div>
            <div className="mt-8">
              <Pagination
                page={page}
                totalPages={totalPages}
                onChange={(p) => {
                  const next = new URLSearchParams(searchParams);
                  next.set("page", p.toString());
                  setSearchParams(next, { replace: true });
                }}
              />
            </div>
          </>
        ) : (
          <EmptyState
            title="No digests yet"
            description="Digests appear here once the daily generation pipeline runs."
          />
        )}
      </div>
    </>
  );
}
