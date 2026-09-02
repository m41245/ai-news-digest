import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Seo } from "../../components/Seo";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Pagination } from "../../components/ui/Pagination";
import { adminApi } from "../../api";
import { ListSkeleton } from "../../components/ui/Skeleton";
import { ErrorState } from "../../components/ui/ErrorState";
import { EmptyState } from "../../components/ui/EmptyState";
import { formatDateTime } from "../../utils";
import type { AdminUser } from "../../types";

const PAGE_SIZE = 20;

export function AdminUsersPage() {
  const qc = useQueryClient();
  const [actionId, setActionId] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["admin-users", page],
    queryFn: () =>
      adminApi.users({ limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }),
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  function toggle(user: AdminUser, field: "is_active" | "is_admin") {
    setActionId(user.id);
    adminApi
      .updateUser(user.id, { [field]: !user[field] })
      .then(() => qc.invalidateQueries({ queryKey: ["admin-users"] }))
      .finally(() => setActionId(null));
  }

  function remove(user: AdminUser) {
    if (!confirm(`Delete user ${user.email}? This cannot be undone.`)) return;
    setActionId(user.id);
    adminApi
      .deleteUser(user.id)
      .then(() => {
        qc.invalidateQueries({ queryKey: ["admin-users"] });
        if (data?.items.length === 1 && page > 1) {
          setPage(page - 1);
        }
      })
      .finally(() => setActionId(null));
  }

  return (
    <>
      <Seo title="User management" noindex />
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Users</h1>
        <p className="mt-1 text-slate-600">Manage registered users and their roles.</p>

        <div className="mt-8">
          {isError && (
            <ErrorState
              message={error?.message ?? "Failed to load users."}
              retry={() => void refetch()}
            />
          )}

          {isLoading ? (
            <ListSkeleton rows={3} />
          ) : data && data.items.length > 0 ? (
            <>
              <Card className="!p-0">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="px-4 py-3 font-medium">Email</th>
                      <th className="px-4 py-3 font-medium">Role</th>
                      <th className="px-4 py-3 font-medium">Status</th>
                      <th className="px-4 py-3 font-medium">Created</th>
                      <th className="px-4 py-3 font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {data.items.map((user) => (
                      <tr key={user.id}>
                        <td className="px-4 py-3 font-medium text-slate-900">
                          {user.email}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={
                              user.is_admin
                                ? "rounded-full bg-brand-100 px-2 py-0.5 text-xs font-medium text-brand-700"
                                : "rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700"
                            }
                          >
                            {user.is_admin ? "Admin" : "Member"}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={
                              user.is_active
                                ? "rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700"
                                : "rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700"
                            }
                          >
                            {user.is_active ? "Active" : "Inactive"}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-500">
                          {formatDateTime(user.created_at)}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              disabled={actionId === user.id}
                              onClick={() => toggle(user, "is_admin")}
                            >
                              {user.is_admin ? "Revoke admin" : "Make admin"}
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              disabled={actionId === user.id}
                              onClick={() => toggle(user, "is_active")}
                            >
                              {user.is_active ? "Deactivate" : "Activate"}
                            </Button>
                            <Button
                              variant="danger"
                              size="sm"
                              disabled={actionId === user.id}
                              onClick={() => remove(user)}
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
              <div className="mt-6 flex justify-center">
                <Pagination
                  page={page}
                  totalPages={totalPages}
                  onChange={setPage}
                />
              </div>
            </>
          ) : (
            <EmptyState title="No users" description="No users have registered yet." />
          )}
        </div>
      </div>
    </>
  );
}
