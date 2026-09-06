export type NotificationDeliveryStatus =
  | "pending"
  | "sent"
  | "delivered"
  | "failed"
  | "deferred"
  | "suppressed";

export type NotificationChannel = "in_app" | "email";

export interface NotificationDeliveryResponse {
  id: string;
  notification_id: string;
  status: NotificationDeliveryStatus;
  channel: NotificationChannel;
  scheduled_for?: string | null;
  sent_at?: string | null;
  delivered_at?: string | null;
  failed_at?: string | null;
  retry_count: number;
  failure_reason?: string | null;
  created_at: string;
  updated_at: string;
}

export interface NotificationDeliveryHistoryResponse {
  items: NotificationDeliveryResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface NotificationStatsResponse {
  total_notifications: number;
  unread_count: number;
  delivered_count: number;
  failed_count: number;
  deferred_count: number;
  suppressed_count: number;
  by_type: Record<string, number>;
  by_severity: Record<string, number>;
  by_channel: Record<string, number>;
}

export interface SchedulePreviewResponse {
  timezone: string;
  next_notification_times: Array<{
    notification_type: string;
    scheduled_for: string;
    reason: string;
  }>;
}

export interface TestNotificationRequest {
  notification_type?: string;
  channel?: NotificationChannel;
  severity?: string;
}
