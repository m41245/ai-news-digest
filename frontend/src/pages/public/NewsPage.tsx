import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Seo } from "../../components/Seo";
import { publicApi } from "../../api";
import { ArticleCard } from "../../components/ArticleCard";
import { Input } from "../../components/ui/Input";
import { ArticleCardSkeleton } from "../../components/ui/Skeleton";
import { ErrorState } from "../../components/ui/ErrorState";
import { EmptyState } from "../../components/ui/EmptyState";
import { Pagination } from "../../components/ui/Pagination";
import { Button } from "../../components/ui/Button";

const PAGE_SIZE = 12;

function FilterGroup({ label, activeValue, options, onSelect, getLabel }: {
  label: string;
  activeValue: string | undefined;
  options: Array<{ id: string; name: string }>;
  onSelect: (value: string | undefined) => void;
  getLabel?: (option: { id: string; name: string }) => string;
}) {
  return (
    <div className="mb-4">
      <span className="block text-sm font-medium text-slate-600 mb-2">{label}</span>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => onSelect(undefined)}
          className={[
            "rounded-full px-3 py-1.5 text-sm font-medium transition-colors",
            !activeValue
              ? "bg-brand-600 text-white"
              : "bg-slate-100 text-slate-700 hover:bg-slate-200",
          ].join(" ")}
        >
          All
        </button>
        {options.map((opt) => (
          <button
            key={opt.id}
            type="button"
            onClick={() => onSelect(opt.id)}
            className={[
              "rounded-full px-3 py-1.5 text-sm font-medium transition-colors",
              activeValue === opt.id
                ? "bg-brand-600 text-white"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200",
            ].join(" ")}
          >
            {getLabel ? getLabel(opt) : opt.name}
          </button>
        ))}
      </div>
    </div>
  );
}

export function NewsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchInput, setSearchInput] = useState(searchParams.get("search") ?? "");
  const [filtersOpen, setFiltersOpen] = useState(true);

  const page = Math.max(1, Number(searchParams.get("page") ?? "1"));
  const categoryId = searchParams.get("category") || undefined;
  const sourceId = searchParams.get("source") || undefined;
  const companyId = searchParams.get("company") || undefined;
  const topicId = searchParams.get("topic") || undefined;
  const search = searchParams.get("search") || undefined;
  const minImportance = searchParams.get("min_importance") || undefined;
  const publishedFrom = searchParams.get("published_from") || undefined;
  const publishedTo = searchParams.get("published_to") || undefined;

  useEffect(() => {
    setSearchInput(searchParams.get("search") ?? "");
  }, [searchParams]);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["articles", { page, categoryId, sourceId, companyId, topicId, search, minImportance, publishedFrom, publishedTo }],
    queryFn: () =>
      publicApi.articles({
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE,
        category_id: categoryId,
        source_id: sourceId,
        company_id: companyId,
        topic_id: topicId,
        search,
        min_importance: minImportance ? Number(minImportance) : undefined,
        published_from: publishedFrom || undefined,
        published_to: publishedTo || undefined,
      }),
  });

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: () => publicApi.categories(),
  });

  const { data: sources } = useQuery({
    queryKey: ["sources"],
    queryFn: () => publicApi.sources(),
  });

  const { data: companies } = useQuery({
    queryKey: ["companies"],
    queryFn: () => publicApi.companies(),
  });

  const { data: topics } = useQuery({
    queryKey: ["topics"],
    queryFn: () => publicApi.topics(),
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

  function clearAllFilters() {
    setSearchParams({}, { replace: true });
    setSearchInput("");
  }

  const hasActiveFilters = categoryId || sourceId || companyId || topicId || search || minImportance || publishedFrom || publishedTo;

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <>
      <Seo
        title="Latest News"
        description="Browse the latest AI-summarized news articles, filtered by category or source."
        canonical="/news"
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

        <div className="mb-4 flex items-center justify-between">
          <button
            type="button"
            onClick={() => setFiltersOpen((o) => !o)}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
            aria-expanded={filtersOpen}
          >
            {filtersOpen ? "Hide filters" : "Show filters"}
            {hasActiveFilters && (
              <span className="inline-flex h-2 w-2 rounded-full bg-brand-600" aria-hidden="true" />
            )}
          </button>
          {hasActiveFilters && (
            <Button variant="secondary" size="sm" onClick={clearAllFilters}>
              Clear all
            </Button>
          )}
        </div>

        {filtersOpen && (
          <div className="mb-6 rounded-xl border border-slate-200 bg-white p-4 sm:p-6">
            <FilterGroup
              label="Category"
              activeValue={categoryId}
              options={categories ?? []}
              onSelect={(v) => updateParam("category", v)}
            />
            <FilterGroup
              label="Source"
              activeValue={sourceId}
              options={sources ?? []}
              onSelect={(v) => updateParam("source", v)}
            />
            <FilterGroup
              label="Company"
              activeValue={companyId}
              options={companies ?? []}
              onSelect={(v) => updateParam("company", v)}
            />
            <FilterGroup
              label="Topic"
              activeValue={topicId}
              options={topics ?? []}
              onSelect={(v) => updateParam("topic", v)}
            />
          </div>
        )}

        {hasActiveFilters && (
          <div className="mb-6 flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-slate-600">Active filters:</span>
            {search && (
              <span className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-3 py-1 text-sm text-brand-700">
                Search: &quot;{search}&quot;
                <button type="button" onClick={() => { updateParam("search", undefined); setSearchInput(""); }} className="text-brand-500 hover:text-brand-700" aria-label={`Remove search filter: ${search}`}>×</button>
              </span>
            )}
            {categoryId && (
              <span className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-3 py-1 text-sm text-brand-700">
                Category
                <button type="button" onClick={() => updateParam("category", undefined)} className="text-brand-500 hover:text-brand-700" aria-label="Remove category filter">×</button>
              </span>
            )}
            {sourceId && (
              <span className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-3 py-1 text-sm text-brand-700">
                Source
                <button type="button" onClick={() => updateParam("source", undefined)} className="text-brand-500 hover:text-brand-700" aria-label="Remove source filter">×</button>
              </span>
            )}
            {companyId && (
              <span className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-3 py-1 text-sm text-brand-700">
                Company
                <button type="button" onClick={() => updateParam("company", undefined)} className="text-brand-500 hover:text-brand-700" aria-label="Remove company filter">×</button>
              </span>
            )}
            {topicId && (
              <span className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-3 py-1 text-sm text-brand-700">
                Topic
                <button type="button" onClick={() => updateParam("topic", undefined)} className="text-brand-500 hover:text-brand-700" aria-label="Remove topic filter">×</button>
              </span>
            )}
            {minImportance && (
              <span className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-3 py-1 text-sm text-brand-700">
                Min importance: {minImportance}
                <button type="button" onClick={() => updateParam("min_importance", undefined)} className="text-brand-500 hover:text-brand-700" aria-label={`Remove minimum importance filter: ${minImportance}`}>×</button>
              </span>
            )}
            {publishedFrom && (
              <span className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-3 py-1 text-sm text-brand-700">
                From: {publishedFrom}
                <button type="button" onClick={() => updateParam("published_from", undefined)} className="text-brand-500 hover:text-brand-700" aria-label={`Remove published from filter: ${publishedFrom}`}>×</button>
              </span>
            )}
            {publishedTo && (
              <span className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-3 py-1 text-sm text-brand-700">
                To: {publishedTo}
                <button type="button" onClick={() => updateParam("published_to", undefined)} className="text-brand-500 hover:text-brand-700" aria-label={`Remove published to filter: ${publishedTo}`}>×</button>
              </span>
            )}
          </div>
        )}

        {isError && (
          <ErrorState
            message={error?.message ?? "Failed to load articles."}
            retry={() => void refetch()}
          />
        )}

        {isLoading ? (
          <div className="grid gap-4 lg:grid-cols-2">
            {Array.from({ length: PAGE_SIZE }).map((_, i) => (
              <ArticleCardSkeleton key={i} />
            ))}
          </div>
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
                <Button variant="secondary" onClick={() => { updateParam("search", undefined); setSearchInput(""); }}>
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
