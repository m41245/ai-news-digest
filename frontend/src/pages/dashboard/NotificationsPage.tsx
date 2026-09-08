import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notificationsApi } from "../../api";
import { type NotificationResponse } from "../../types";
import { Seo } from "../../components/Seo";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Spinner } from "../../components/ui/Spinner";
import { ErrorState } from "../../components/ui/ErrorState";
import { EmptyState } from "../../components/ui/EmptyState";
import { Badge } from "../../components/ui/Badge";
import { NotificationTypeIcon } from "../../components/notifications/NotificationTypeIcon";
import { formatDateTime } from "../../utils";

type SortOption = "newest" | "oldest" | "severity";

const severityOrder: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

export function NotificationsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<SortOption>("newest");
  const [filterType, setFilterType] = useState<string>("");

  const pageSize = 20;

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["notifications", page, sort, filterType],
    queryFn: () =>
      notificationsApi.list({
        limit: pageSize,
        offset: (page - 1) * pageSize,
        unread_only: false,
        notification_type: filterType || undefined,
      }),
  });

  const markReadMutation = useMutation({
    mutationFn: (id: string) => notificationsApi.markRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      queryClient.invalidateQueries({ queryKey: ["notification-unread-count"] });
    },
  });

  const markAllReadMutation = useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      queryClient.invalidateQueries({ queryKey: ["notification-unread-count"] });
    },
  });

  const dismissMutation = useMutation({
    mutationFn: (id: string) => notificationsApi.dismiss(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const notifications = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const sortedNotifications = useMemo(() => {
    const items = [...notifications];
    switch (sort) {
      case "oldest":
        return items.sort((a, b) => (a.created_at ?? "").localeCompare(b.created_at ?? ""));
      case "severity":
        return items.sort((a, b) => (severityOrder[a.severity] ?? 99) - (severityOrder[b.severity] ?? 99));
      case "newest":
      default:
        return items.sort((a, b) => (b.created_at ?? "").localeCompare(a.created_at ?? ""));
    }
  }, [notifications, sort]);

  const availableTypes = useMemo(() => {
    const types = new Set(notifications.map((n) => n.notification_type));
    return Array.from(types).sort();
  }, [notifications]);

  const getSeverityTone = (severity: string): "neutral" | "brand" | "success" | "warning" | "danger" => {
    switch (severity) {
      case "critical":
        return "danger";
      case "high":
        return "warning";
      case "medium":
        return "warning";
      case "low":
        return "brand";
      default:
        return "neutral";
    }
  };

  const getTypeLabel = (type: string) => {
    return type
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  };

  return (
    <>
      <Seo title="Notifications" noindex />
      <div className="container-page py-8">
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Notifications</h1>
            <p className="mt-1 text-slate-600">
              Stay updated with the latest intelligence.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              onClick={() => markAllReadMutation.mutate()}
              disabled={markAllReadMutation.isPending}
            >
              Mark all read
            </Button>
            <Button variant="ghost">
              <Link to="/notifications/preferences" className="text-sm text-brand-600 hover:text-brand-700">
                Notification settings
              </Link>
            </Button>
          </div>
        </div>

        <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <label htmlFor="sort" className="text-sm font-medium text-slate-700">
              Sort by
            </label>
            <select
              id="sort"
              value={sort}
              onChange={(e) => {
                setSort(e.target.value as SortOption);
                setPage(1);
              }}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
            >
              <option value="newest">Newest</option>
              <option value="oldest">Oldest</option>
              <option value="severity">Severity</option>
            </select>
            {availableTypes.length > 0 && (
              <>
                <label htmlFor="filter-type" className="text-sm font-medium text-slate-700 ml-2">
                  Filter by type
                </label>
                <select
                  id="filter-type"
                  value={filterType}
                  onChange={(e) => {
                    setFilterType(e.target.value);
                    setPage(1);
                  }}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                >
                  <option value="">All types</option>
                  {availableTypes.map((type) => (
                    <option key={type} value={type}>
                      {getTypeLabel(type)}
                    </option>
                  ))}
                </select>
              </>
            )}
          </div>
        </div>

        {isError && (
          <ErrorState
            message={error?.message ?? "Failed to load notifications."}
            retry={() => void refetch()}
          />
        )}

        {isLoading ? (
          <Spinner label="Loading notifications" />
        ) : sortedNotifications.length === 0 ? (
          <EmptyState
            title="No notifications yet"
            description="We will notify you when there is relevant intelligence."
          />
        ) : (
          <div className="space-y-4">
            {sortedNotifications.map((notification: NotificationResponse) => {
              return (
                <Card
                  key={notification.id}
                  className={`transition-colors ${
                    notification.read_at ? "opacity-75" : "border-l-4 border-l-brand-500"
                  }`}
                >
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <NotificationTypeIcon type={notification.notification_type} />
                        <Badge tone={getSeverityTone(notification.severity)}>
                          {notification.severity}
                        </Badge>
                        <span className="text-xs text-slate-500 capitalize">
                          {getTypeLabel(notification.notification_type)}
                        </span>
                        {!notification.read_at && (
                          <span className="inline-flex h-2 w-2 rounded-full bg-brand-500" aria-label="Unread" />
                        )}
                      </div>
                      <h3 className="mt-2 font-semibold text-slate-900">
                        {notification.title}
                      </h3>
                      <p className="mt-1 text-sm text-slate-600">{notification.body}</p>
                      <p className="mt-2 text-xs text-slate-400">
                        {formatDateTime(notification.created_at)}
                      </p>
                    </div>
                    <div className="flex shrink-0 gap-2 lg:flex-col xl:flex-row">
                      {!notification.read_at && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => markReadMutation.mutate(notification.id)}
                          aria-label={`Mark notification ${notification.id} as read`}
                        >
                          Mark read
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => dismissMutation.mutate(notification.id)}
                        aria-label={`Dismiss notification ${notification.id}`}
                      >
                        Dismiss
                      </Button>
                    </div>
                  </div>
                </Card>
              );
            })}

            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-4">
                <Button
                  variant="secondary"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  aria-label="Previous page of notifications"
                >
                  Previous
                </Button>
                <span className="text-sm text-slate-500">
                  Page {page} of {totalPages}
                </span>
                <Button
                  variant="secondary"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  aria-label="Next page of notifications"
                >
                  Next
                </Button>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
}
