import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { notificationsApi } from "../../api";
import { Seo } from "../../components/Seo";
import { Card } from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { ErrorState } from "../../components/ui/ErrorState";
import { Pagination } from "../../components/ui/Pagination";
import { DeliveryStatusBadge } from "../../components/notifications/DeliveryStatusBadge";
import { formatDateTime } from "../../utils";
import type { NotificationDeliveryStatus } from "../../types";

const pageSize = 20;

export function NotificationDeliveryHistoryPage() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>("");

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["notification-deliveries", page, statusFilter],
    queryFn: () =>
      notificationsApi.deliveries.list({
        limit: pageSize,
        offset: (page - 1) * pageSize,
        status: (statusFilter as NotificationDeliveryStatus) || undefined,
      }),
  });

  const deliveries = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const uniqueStatuses = useMemo(() => {
    const statuses = new Set(deliveries.map((d) => d.status));
    return Array.from(statuses).sort();
  }, [deliveries]);

  return (
    <>
      <Seo title="Delivery History" noindex />
      <div className="container-page py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-slate-900">Delivery History</h1>
          <p className="mt-1 text-slate-600">
            Track the delivery status of your notifications.
          </p>
        </div>

        <div className="mb-6">
          <label htmlFor="status-filter" className="text-sm font-medium text-slate-700">
            Filter by status
          </label>
          <select
            id="status-filter"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="mt-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
          >
            <option value="">All statuses</option>
            {uniqueStatuses.map((status) => (
              <option key={status} value={status}>
                {status.charAt(0).toUpperCase() + status.slice(1)}
              </option>
            ))}
          </select>
        </div>

        {isError && (
          <ErrorState
            message={error?.message ?? "Failed to load delivery history."}
            retry={() => void refetch()}
          />
        )}

        {isLoading ? (
          <Spinner label="Loading delivery history" />
        ) : deliveries.length === 0 ? (
          <Card>
            <div className="py-12 text-center">
              <p className="text-lg font-medium text-slate-900">No deliveries found</p>
              <p className="mt-1 text-slate-500">
                Delivery attempts will appear here once notifications are sent.
              </p>
            </div>
          </Card>
        ) : (
          <div className="space-y-4">
            {deliveries.map((delivery) => (
              <Card key={delivery.id} className="transition-colors">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <DeliveryStatusBadge status={delivery.status} />
                      <span className="text-xs text-slate-500 capitalize">
                        {delivery.channel === "email" ? "📧" : "🔔"} {delivery.channel}
                      </span>
                      {delivery.retry_count > 0 && (
                        <span className="text-xs text-slate-500">
                          Retries: {delivery.retry_count}
                        </span>
                      )}
                    </div>
                    <p className="mt-2 text-sm text-slate-600">
                      Notification ID: <span className="font-mono text-xs">{delivery.notification_id}</span>
                    </p>
                    {delivery.scheduled_for && (
                      <p className="mt-1 text-xs text-slate-500">
                        Scheduled for: {formatDateTime(delivery.scheduled_for)}
                      </p>
                    )}
                    {delivery.sent_at && (
                      <p className="text-xs text-slate-500">
                        Sent: {formatDateTime(delivery.sent_at)}
                      </p>
                    )}
                    {delivery.delivered_at && (
                      <p className="text-xs text-slate-500">
                        Delivered: {formatDateTime(delivery.delivered_at)}
                      </p>
                    )}
                    {delivery.failed_at && (
                      <p className="text-xs text-red-600">
                        Failed: {formatDateTime(delivery.failed_at)}
                      </p>
                    )}
                    {delivery.failure_reason && (
                      <p className="mt-2 text-xs text-red-700 bg-red-50 rounded-md px-3 py-2">
                        Reason: {delivery.failure_reason}
                      </p>
                    )}
                    <p className="mt-2 text-xs text-slate-400">
                      Created: {formatDateTime(delivery.created_at)} · Updated: {formatDateTime(delivery.updated_at)}
                    </p>
                  </div>
                </div>
              </Card>
            ))}

            {totalPages > 1 && (
              <Pagination page={page} totalPages={totalPages} onChange={setPage} />
            )}
          </div>
        )}
      </div>
    </>
  );
}
