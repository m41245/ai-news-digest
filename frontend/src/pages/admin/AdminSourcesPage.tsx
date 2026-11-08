import React, { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Seo } from "../../components/Seo";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { sourcesApi } from "../../api";
import { ListSkeleton } from "../../components/ui/Skeleton";
import { ErrorState } from "../../components/ui/ErrorState";
import { EmptyState } from "../../components/ui/EmptyState";
import { Fieldset } from "../../components/ui/Input";

export function AdminSourcesPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [feedUrl, setFeedUrl] = useState("");
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["admin-sources"],
    queryFn: () => sourcesApi.list({ limit: 100 }),
  });

  async function createSource(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await sourcesApi.create({
        name: name.trim(),
        feed_url: feedUrl.trim(),
        website_url: websiteUrl.trim() || null,
      });
      setName("");
      setFeedUrl("");
      setWebsiteUrl("");
      qc.invalidateQueries({ queryKey: ["admin-sources"] });
    } finally {
      setSubmitting(false);
    }
  }

  async function toggleActive(id: string, current: boolean) {
    setPendingId(id);
    setActionError(null);
    setActionSuccess(null);
    try {
      if (current) {
        await sourcesApi.deactivate(id, { reason: "Disabled by administrator" });
      } else {
        await sourcesApi.approve(id, { reason: "Approved by administrator" });
      }
      setActionSuccess(id);
      qc.invalidateQueries({ queryKey: ["admin-sources"] });
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Action failed.");
    } finally {
      setPendingId(null);
    }
  }

  async function removeSource(id: string) {
    if (!confirm("Delete this source?")) return;
    await sourcesApi.remove(id);
    qc.invalidateQueries({ queryKey: ["admin-sources"] });
  }

  return (
    <>
      <Seo title="Source management" noindex />
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Sources</h1>
        <p className="mt-1 text-slate-600">Manage RSS news sources.</p>

        <Card className="mt-8">
          <h2 className="text-lg font-semibold text-slate-900">Add a source</h2>
          <form onSubmit={createSource} className="mt-4">
            <Fieldset>
              <div className="grid gap-4 sm:grid-cols-2">
                <Input
                  label="Name"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Hacker News"
                />
                <Input
                  label="Feed URL"
                  type="url"
                  required
                  value={feedUrl}
                  onChange={(e) => setFeedUrl(e.target.value)}
                  placeholder="https://…"
                />
              </div>
              <Input
                label="Website URL (optional)"
                type="url"
                value={websiteUrl}
                onChange={(e) => setWebsiteUrl(e.target.value)}
                placeholder="https://…"
              />
              <div>
                <Button type="submit" disabled={submitting}>
                  {submitting ? "Adding…" : "Add source"}
                </Button>
              </div>
            </Fieldset>
          </form>
        </Card>

        <div className="mt-8">
          {actionError && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {actionError}
            </div>
          )}
          {actionSuccess && (
            <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">
              Source updated successfully.
            </div>
          )}
          {isError && (
            <ErrorState
              message={error?.message ?? "Failed to load sources."}
              retry={() => void refetch()}
            />
          )}

          {isLoading ? (
            <ListSkeleton rows={3} />
          ) : data && data.items.length > 0 ? (
            <Card className="!p-0">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-4 py-3 font-medium">Name</th>
                    <th className="hidden px-4 py-3 font-medium sm:table-cell">Feed URL</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {data.items.map((s) => (
                    <tr key={s.id}>
                      <td className="px-4 py-3 font-medium text-slate-900">{s.name}</td>
                      <td className="hidden max-w-xs truncate px-4 py-3 text-slate-500 sm:table-cell">
                        {s.feed_url}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={
                            s.status === "verified"
                              ? "rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700"
                              : s.status === "pending_review"
                                ? "rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700"
                                : s.status === "rejected"
                                  ? "rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700"
                                  : "rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700"
                          }
                        >
                          {s.status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            disabled={pendingId === s.id}
                            onClick={() => toggleActive(s.id, s.is_active)}
                          >
                            {pendingId === s.id
                              ? "Working…"
                              : s.is_active
                                ? "Disable"
                                : "Enable"}
                          </Button>
                          <Button
                            variant="danger"
                            size="sm"
                            onClick={() => removeSource(s.id)}
                          >
                            Delete
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          ) : (
            <EmptyState title="No sources" description="Add your first RSS source above." />
          )}
        </div>
      </div>
    </>
  );
}
