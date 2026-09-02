import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Seo } from "../../components/Seo";
import { publicApi } from "../../api";
import { ArticleCard } from "../../components/ArticleCard";
import { Input } from "../../components/ui/Input";
import { ListSkeleton } from "../../components/ui/Skeleton";
import { ErrorState } from "../../components/ui/ErrorState";
import { EmptyState } from "../../components/ui/EmptyState";
import { Pagination } from "../../components/ui/Pagination";
import { Button } from "../../components/ui/Button";
import type { Category } from "../../types";

const PAGE_SIZE = 12;

export function NewsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchInput, setSearchInput] = useState(searchParams.get("search") ?? "");

  const page = Math.max(1, Number(searchParams.get("page") ?? "1"));
  const categoryId = searchParams.get("category") || undefined;
  const sourceId = searchParams.get("source") || undefined;
  const search = searchParams.get("search") || undefined;

  useEffect(() => {
    setSearchInput(searchParams.get("search") ?? "");
  }, [searchParams]);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["articles", { page, categoryId, sourceId, search }],
    queryFn: () =>
      publicApi.articles({
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE,
        category_id: categoryId,
        source_id: sourceId,
        search,
      }),
  });

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: () => publicApi.categories(),
  });

  function updateParam(key: string, value: string | undefined) {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    next.delete("page");
    setSearchParams(next, { replace: true });
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    updateParam("search", searchInput.trim() || undefined);
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <>
      <Seo
        title="Latest News"
        description="Browse the latest AI-summarized news articles, filtered by category or source."
      />
      <div className="container-page py-8">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Latest News</h1>
            <p className="mt-1 text-slate-600">
              AI-summarized articles from trusted sources.
            </p>
          </div>
          <form onSubmit={handleSearch} role="search" className="flex gap-2">
            <Input
              placeholder="Search articles…"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              aria-label="Search articles"
              className="w-64"
            />
            <Button type="submit">Search</Button>
          </form>
        </div>

        {categories && categories.length > 0 && (
          <div className="mb-6 flex flex-wrap gap-2">
            <span className="py-1 text-sm font-medium text-slate-600">
              Category:
            </span>
            <button
              type="button"
              onClick={() => updateParam("category", undefined)}
              className={[
                "rounded-full px-3 py-1 text-sm font-medium transition-colors",
                !categoryId
                  ? "bg-brand-600 text-white"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200",
              ].join(" ")}
            >
              All
            </button>
            {categories.map((c: Category) => (
              <button
                key={c.id}
                type="button"
                onClick={() => updateParam("category", c.id)}
                className={[
                  "rounded-full px-3 py-1 text-sm font-medium transition-colors",
                  categoryId === c.id
                    ? "bg-brand-600 text-white"
                    : "bg-slate-100 text-slate-700 hover:bg-slate-200",
                ].join(" ")}
              >
                {c.name}
              </button>
            ))}
          </div>
        )}

        {isError && (
          <ErrorState
            message={error?.message ?? "Failed to load articles."}
            retry={() => void refetch()}
          />
        )}

        {isLoading ? (
          <ListSkeleton rows={4} />
        ) : data && data.items.length > 0 ? (
          <>
            <p className="mb-4 text-sm text-slate-500">
              {data.total} article{data.total === 1 ? "" : "s"}
              {search && ` matching "${search}"`}
            </p>
            <div className="grid gap-4 lg:grid-cols-2">
              {data.items.map((article) => (
                <ArticleCard key={article.id} article={article} />
              ))}
            </div>
            <div className="mt-8">
              <Pagination
                page={page}
                totalPages={totalPages}
                onChange={(p) => updateParam("page", p.toString())}
              />
            </div>
          </>
        ) : (
          <EmptyState
            title="No articles found"
            description={
              search
                ? "Try a different search term or clear the filters."
                : "Articles will appear here once the ingestion pipeline runs."
            }
            action={
              search ? (
                <Button variant="secondary" onClick={() => updateParam("search", undefined)}>
                  Clear search
                </Button>
              ) : undefined
            }
          />
        )}
      </div>
    </>
  );
}
