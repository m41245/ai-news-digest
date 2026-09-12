export interface ApiError {
  detail: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface Category {
  id: string;
  name: string;
  description?: string | null;
}

export interface Source {
  id: string;
  name: string;
  feed_url: string;
  website_url?: string | null;
  description?: string | null;
  is_active: boolean;
  status: string;
}

export interface Article {
  id: string;
  title: string;
  url: string;
  summary?: string | null;
  content?: string | null;
  status: string;
  published_at?: string | null;
  fetched_at?: string | null;
  source_id?: string | null;
  category_id?: string | null;
  source_name?: string | null;
  category_name?: string | null;
}

export interface Digest {
  id: string;
  title: string;
  content: string;
  format: string;
  generated_at: string;
  article_ids: string[];
}

export interface PublicDigest {
  id: string;
  title: string;
  content: string;
  format: string;
  generated_at: string;
  article_count: number;
}

export interface User {
  id: string;
  email: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface UserUpdateRequest {
  email?: string;
  password?: string;
}

export interface AdminUser {
  id: string;
  email: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface AdminUserUpdateRequest {
  email?: string;
  is_active?: boolean;
  is_admin?: boolean;
  password?: string;
}

export interface SourceCreateRequest {
  name: string;
  feed_url: string;
  website_url?: string | null;
  description?: string | null;
}

export interface SourceUpdateRequest {
  name?: string;
  feed_url?: string | null;
  website_url?: string | null;
  description?: string | null;
  is_active?: boolean;
  status?: string | null;
}

export interface DigestCreateRequest {
  title: string;
  content: string;
  limit?: number;
}

export interface SystemStats {
  articles: number;
  sources: number;
  digests: number;
  status: string;
}

export interface IngestionResponse {
  message: string;
  task_id: string;
}

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

export interface NotificationPreferenceResponse {
  user_id: string;
  in_app_enabled: boolean;
  email_enabled: boolean;
  immediate_enabled: boolean;
  daily_digest_enabled: boolean;
  weekly_digest_enabled: boolean;
  min_importance: number;
  min_confidence: number;
  notify_followed_companies: boolean;
  notify_followed_topics: boolean;
  notify_corrections: boolean;
  notify_story_evolution: boolean;
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
  timezone: string;
  max_per_day: number;
}

export interface NotificationPreferenceUpdateRequest {
  in_app_enabled?: boolean;
  email_enabled?: boolean;
  immediate_enabled?: boolean;
  daily_digest_enabled?: boolean;
  weekly_digest_enabled?: boolean;
  min_importance?: number;
  min_confidence?: number;
  notify_followed_companies?: boolean;
  notify_followed_topics?: boolean;
  notify_corrections?: boolean;
  notify_story_evolution?: boolean;
  quiet_hours_start?: string | null;
  quiet_hours_end?: string | null;
  timezone?: string;
  max_per_day?: number;
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
