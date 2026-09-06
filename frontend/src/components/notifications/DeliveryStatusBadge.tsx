import type { NotificationDeliveryStatus } from "../../types";
import { cn } from "../../utils";

const statusClasses: Record<NotificationDeliveryStatus, string> = {
  pending: "bg-slate-100 text-slate-700",
  sent: "bg-brand-100 text-brand-700",
  delivered: "bg-emerald-100 text-emerald-700",
  failed: "bg-red-100 text-red-700",
  deferred: "bg-amber-100 text-amber-700",
  suppressed: "bg-orange-100 text-orange-700",
};

const statusLabels: Record<NotificationDeliveryStatus, string> = {
  pending: "Pending",
  sent: "Sent",
  delivered: "Delivered",
  failed: "Failed",
  deferred: "Deferred",
  suppressed: "Suppressed",
};

type DeliveryStatusBadgeProps = {
  status: NotificationDeliveryStatus;
  className?: string;
};

export function DeliveryStatusBadge({ status, className }: DeliveryStatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        statusClasses[status] ?? "bg-slate-100 text-slate-700",
        className,
      )}
    >
      {statusLabels[status] ?? status}
    </span>
  );
}
