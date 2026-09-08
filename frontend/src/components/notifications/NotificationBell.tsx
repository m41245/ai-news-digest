import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notificationsApi } from "../../api";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { NotificationTypeIcon } from "./NotificationTypeIcon";

function timeAgo(dateString: string | null): string {
  if (!dateString) return "";
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

const severityToneMap: Record<string, "neutral" | "brand" | "success" | "warning" | "danger"> = {
  critical: "danger",
  high: "warning",
  medium: "warning",
  low: "brand",
};

export function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false);
  const queryClient = useQueryClient();

  const { data: countData } = useQuery({
    queryKey: ["notification-unread-count"],
    queryFn: () => notificationsApi.unreadCount(),
    refetchInterval: 60000,
  });

  const markReadMutation = useMutation({
    mutationFn: (id: string) => notificationsApi.markRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notification-unread-count"] });
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const markAllReadMutation = useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notification-unread-count"] });
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const unreadCountValue = countData?.unread_count ?? 0;

  return (
    <div className="relative">
      <Button
        variant="ghost"
        size="sm"
        aria-label={`Notifications, ${unreadCountValue} unread`}
        aria-expanded={isOpen}
        aria-haspopup="true"
        onClick={() => setIsOpen(!isOpen)}
        className="relative"
      >
        <svg
          className="h-5 w-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
          />
        </svg>
        {unreadCountValue > 0 && (
          <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-xs font-bold text-white">
            {unreadCountValue > 9 ? "9+" : unreadCountValue}
          </span>
        )}
      </Button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-20" onClick={() => setIsOpen(false)} />
          <Card className="absolute right-0 z-30 mt-2 w-80 p-0 shadow-lg">
            <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
              <h3 className="font-semibold text-slate-900">Notifications</h3>
              {unreadCountValue > 0 && (
                <button
                  onClick={() => markAllReadMutation.mutate()}
                  className="text-sm text-brand-600 hover:text-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 rounded"
                >
                  Mark all read
                </button>
              )}
            </div>
            <NotificationDropdownContent
              onRead={(id) => markReadMutation.mutate(id)}
              onClose={() => setIsOpen(false)}
            />
            <div className="border-t border-slate-200 px-4 py-2">
              <Link
                to="/notifications"
                className="block text-center text-sm text-brand-600 hover:text-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 rounded"
                onClick={() => setIsOpen(false)}
              >
                View all notifications
              </Link>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

function NotificationDropdownContent({
  onRead,
  onClose,
}: {
  onRead: (id: string) => void;
  onClose: () => void;
}) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["notifications-dropdown"],
    queryFn: () => notificationsApi.list({ limit: 5, unread_only: true }),
  });

  if (isLoading) {
    return (
      <div className="p-4">
        <p className="text-sm text-slate-500">Loading notifications...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4">
        <p className="text-sm text-red-600" role="alert">Failed to load notifications.</p>
      </div>
    );
  }

  const items = data?.items ?? [];

  if (items.length === 0) {
    return (
      <div className="p-4">
        <p className="text-sm text-slate-500">No new notifications.</p>
      </div>
    );
  }

  return (
    <ul className="max-h-80 overflow-y-auto" role="list">
      {items.map((notification) => (
        <li
          key={notification.id}
          className={`border-b border-slate-100 last:border-b-0 ${
            notification.read_at ? "opacity-60" : ""
          }`}
        >
          <Link
            to={notification.story_id ? `/stories/${notification.story_id}` : "/notifications"}
            className="block px-4 py-3 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-inset"
            onClick={() => {
              if (!notification.read_at) {
                onRead(notification.id);
              }
              onClose();
            }}
          >
            <div className="flex items-start gap-2">
              <NotificationTypeIcon type={notification.notification_type} className="mt-0.5" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium text-slate-900 truncate">
                    {notification.title}
                  </p>
                  <div className="flex items-center gap-1.5 shrink-0">
                    {!notification.read_at && (
                      <span className="mt-0.5 h-2 w-2 flex-shrink-0 rounded-full bg-brand-500" />
                    )}
                  </div>
                </div>
                <div className="mt-1 flex items-center gap-2 flex-wrap">
                  <Badge tone={severityToneMap[notification.severity] ?? "neutral"} className="text-[10px]">
                    {notification.severity}
                  </Badge>
                  <span className="text-[10px] text-slate-500 capitalize">
                    {notification.notification_type.replace(/_/g, " ")}
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-500 line-clamp-2">{notification.body}</p>
                <p className="mt-1 text-xs text-slate-400">
                  {notification.created_at ? timeAgo(notification.created_at) : ""}
                </p>
              </div>
            </div>
          </Link>
        </li>
      ))}
    </ul>
  );
}
