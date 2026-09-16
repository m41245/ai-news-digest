export type NotificationDeliveryStatus =
  | "pending"
  | "sent"
  | "delivered"
  | "failed"
  | "deferred"
  | "suppressed";

export type NotificationChannel = "in_app" | "email";

export interface NotificationResponse {
  id: string;
  user_id: string;
  notification_type: string;
  title: string;
  body: string;
  severity: string;
  story_id: string | null;
  article_id: string | null;
  company_id: string | null;
  topic_id: string | null;
  digest_id: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string | null;
  read_at: string | null;
  dismissed_at: string | null;
  expires_at: string | null;
}

export interface NotificationDeliveryResponse {
  id: string;
  notification_id: string;
  channel: string;
  status: string;
  provider_message_id?: string | null;
  attempt_count: number;
  last_attempt_at?: string | null;
  delivered_at?: string | null;
  failure_reason?: string | null;
  created_at?: string | null;
  scheduled_for?: string | null;
  next_attempt_at?: string | null;
  delivery_window?: string | null;
  suppression_reason?: string | null;
}

export interface NotificationDeliveryHistoryResponse {
  items: NotificationDeliveryResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface NotificationStatsResponse {
  total: number;
  unread: number;
  by_type: Record<string, number>;
  by_severity: Record<string, number>;
  deliveries_pending: number;
  deliveries_sent: number;
  deliveries_failed: number;
}

export interface SchedulePreviewResponse {
  scheduled: NotificationDeliveryResponse[];
  count: number;
}

export interface TestNotificationRequest {
  notification_type?: string;
  title?: string;
  body?: string;
  severity?: string;
}
