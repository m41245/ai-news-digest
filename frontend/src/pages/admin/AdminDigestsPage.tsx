import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Seo } from "../../components/Seo";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Input, Fieldset } from "../../components/ui/Input";
import { digestsApi } from "../../api";
import { ListSkeleton } from "../../components/ui/Skeleton";
import { ErrorState } from "../../components/ui/ErrorState";
import { EmptyState } from "../../components/ui/EmptyState";
import { formatDateTime } from "../../utils";

export function AdminDigestsPage() {
  const qc = useQueryClient();
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["admin-digests"],
    queryFn: () => digestsApi.list({ limit: 100 }),
  });

  async function createDigest(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await digestsApi.generate({ title: title.trim(), content: content.trim() });
      setTitle("");
      setContent("");
      qc.invalidateQueries({ queryKey: ["admin-digests"] });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <Seo title="Digest management" noindex />
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Digests</h1>
        <p className="mt-1 text-slate-600">Generate and review digests.</p>

        <Card className="mt-8">
          <h2 className="text-lg font-semibold text-slate-900">Generate a digest</h2>
          <form onSubmit={createDigest} className="mt-4">
            <Fieldset>
              <Input
                label="Title"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-slate-700">Content</label>
                <textarea
                  required
                  rows={6}
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500"
                  placeholder="Markdown content…"
                />
              </div>
              <div>
                <Button type="submit" disabled={submitting}>
                  {submitting ? "Generating…" : "Generate digest"}
                </Button>
              </div>
            </Fieldset>
          </form>
        </Card>

        <div className="mt-8">
          {isError && (
            <ErrorState
              message={error?.message ?? "Failed to load digests."}
              retry={() => void refetch()}
            />
          )}

          {isLoading ? (
            <ListSkeleton rows={3} />
          ) : data && data.items.length > 0 ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {data.items.map((d) => (
                <Card key={d.id} as="article">
                  <h3 className="text-base font-semibold text-slate-900">{d.title}</h3>
                  <p className="mt-1 text-sm text-slate-500">
                    {formatDateTime(d.generated_at)} &middot;{" "}
                    {d.article_ids.length} article{d.article_ids.length === 1 ? "" : "s"}
                  </p>
                </Card>
              ))}
            </div>
          ) : (
            <EmptyState title="No digests" description="Generate your first digest above." />
          )}
        </div>
      </div>
    </>
  );
}
