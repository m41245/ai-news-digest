import { api, getStoredToken, setStoredToken } from "./client";
import type {
  AdminUser,
  AdminUserUpdateRequest,
  Article,
  Category,
  Digest,
  DigestCreateRequest,
  IngestionResponse,
  LoginRequest,
  LoginResponse,
  NotificationDeliveryHistoryResponse,
  NotificationDeliveryResponse,
  NotificationDeliveryStatus,
  NotificationResponse,
  PaginatedResponse,
  PublicDigest,
  RegisterRequest,
  Source,
  SourceCreateRequest,
  SourceUpdateRequest,
  SystemStats,
  User,
  UserUpdateRequest,
} from "../types";

export const authApi = {
  login: (data: LoginRequest): Promise<LoginResponse> =>
    api.post("/api/v1/auth/login", data).then((r) => r.data),
  register: (data: RegisterRequest): Promise<User> =>
    api.post("/api/v1/auth/register", data).then((r) => r.data),
  logout: (): Promise<{ message: string }> =>
    api.post("/api/v1/auth/logout").then((r) => r.data),
  me: (): Promise<User> => api.get("/api/v1/auth/me").then((r) => r.data),
};

export const usersApi = {
  getMe: (): Promise<User> => api.get("/api/v1/users/me").then((r) => r.data),
  updateMe: (data: UserUpdateRequest): Promise<User> =>
    api.patch("/api/v1/users/me", data).then((r) => r.data),
};

export const publicApi = {
  articles: (params: {
    limit?: number;
    offset?: number;
    category_id?: string;
    source_id?: string;
    search?: string;
  } = {}): Promise<PaginatedResponse<Article>> =>
    api.get("/api/v1/public/articles", { params }).then((r) => r.data),
  article: (id: string): Promise<Article> =>
    api.get(`/api/v1/public/articles/${id}`).then((r) => r.data),
  digests: (params: { limit?: number; offset?: number } = {}): Promise<
    PaginatedResponse<PublicDigest>
  > => api.get("/api/v1/public/digests", { params }).then((r) => r.data),
  digest: (id: string): Promise<PublicDigest> =>
    api.get(`/api/v1/public/digests/${id}`).then((r) => r.data),
  categories: (): Promise<Category[]> =>
    api.get("/api/v1/public/categories").then((r) => r.data),
  search: (q: string, limit = 20): Promise<PaginatedResponse<Article>> =>
    api
      .get("/api/v1/public/articles", { params: { search: q, limit } })
      .then((r) => r.data),
};

export const articlesApi = {
  list: (params: { limit?: number; offset?: number } = {}): Promise<
    PaginatedResponse<Article>
  > => api.get("/api/v1/articles", { params }).then((r) => r.data),
  get: (id: string): Promise<Article> =>
    api.get(`/api/v1/articles/${id}`).then((r) => r.data),
};

export const sourcesApi = {
  list: (params: { limit?: number; offset?: number } = {}): Promise<
    PaginatedResponse<Source>
  > => api.get("/api/v1/sources", { params }).then((r) => r.data),
  create: (data: SourceCreateRequest): Promise<Source> =>
    api.post("/api/v1/sources", data).then((r) => r.data),
  update: (id: string, data: SourceUpdateRequest): Promise<Source> =>
    api.patch(`/api/v1/sources/${id}`, data).then((r) => r.data),
  remove: (id: string): Promise<void> =>
    api.delete(`/api/v1/sources/${id}`).then((r) => r.data),
};

export const digestsApi = {
  list: (params: { limit?: number; offset?: number } = {}): Promise<
    PaginatedResponse<Digest>
  > => api.get("/api/v1/digests", { params }).then((r) => r.data),
  get: (id: string): Promise<Digest> =>
    api.get(`/api/v1/digests/${id}`).then((r) => r.data),
  generate: (data: DigestCreateRequest): Promise<Digest> =>
    api.post("/api/v1/digests/generate", data).then((r) => r.data),
};

export const notificationsApi = {
  list: (params: {
    limit?: number;
    offset?: number;
    unread_only?: boolean;
    notification_type?: string;
  } = {}): Promise<PaginatedResponse<NotificationResponse>> =>
    api.get("/api/v1/notifications/", { params }).then((r) => r.data),
  get: (id: string): Promise<NotificationResponse> =>
    api.get(`/api/v1/notifications/${id}`).then((r) => r.data),
  markRead: (id: string): Promise<NotificationResponse> =>
    api.post(`/api/v1/notifications/${id}/read`).then((r) => r.data),
  markAllRead: (): Promise<{ unread_count: number }> =>
    api.post("/api/v1/notifications/read-all").then((r) => r.data),
  dismiss: (id: string): Promise<NotificationResponse> =>
    api.post(`/api/v1/notifications/${id}/dismiss`).then((r) => r.data),
  unreadCount: (): Promise<{ unread_count: number }> =>
    api.get("/api/v1/notifications/unread/count").then((r) => r.data),
  deliveries: {
    list: (params: {
      limit?: number;
      offset?: number;
      status?: NotificationDeliveryStatus;
    } = {}): Promise<NotificationDeliveryHistoryResponse> =>
      api.get("/api/v1/notifications/deliveries", { params }).then((r) => r.data),
    get: (id: string): Promise<NotificationDeliveryResponse> =>
      api.get(`/api/v1/notifications/deliveries/${id}`).then((r) => r.data),
  },
  preferences: {
    get: (): Promise<import("../types").NotificationPreferenceResponse> =>
      api.get("/api/v1/notifications/preferences").then((r) => r.data),
    update: (data: import("../types").NotificationPreferenceUpdateRequest): Promise<import("../types").NotificationPreferenceResponse> =>
      api.put("/api/v1/notifications/preferences", data).then((r) => r.data),
    reset: (): Promise<import("../types").NotificationPreferenceResponse> =>
      api.post("/api/v1/notifications/preferences/reset").then((r) => r.data),
  },
  stats: (): Promise<import("../types").NotificationStatsResponse> =>
    api.get("/api/v1/notifications/stats").then((r) => r.data),
  schedulePreview: (): Promise<import("../types").SchedulePreviewResponse> =>
    api.get("/api/v1/notifications/schedule-preview").then((r) => r.data),
};

export const adminApi = {
  users: (params: { limit?: number; offset?: number } = {}): Promise<
    import("../types").PaginatedResponse<AdminUser>
  > =>
    api.get("/api/v1/admin/users", { params }).then((r) => r.data),
  updateUser: (id: string, data: AdminUserUpdateRequest): Promise<AdminUser> =>
    api.patch(`/api/v1/admin/users/${id}`, data).then((r) => r.data),
  deleteUser: (id: string): Promise<void> =>
    api.delete(`/api/v1/admin/users/${id}`).then((r) => r.data),
  stats: (): Promise<SystemStats> =>
    api.get("/api/v1/admin/stats").then((r) => r.data),
  pipelineStatus: (): Promise<{
    status: string;
    warnings?: string[];
    ingestion: { last_attempt: string | null; last_success: string | null };
    processing: { last_attempt: string | null; last_success: string | null };
    digest: { last_attempt: string | null; last_generated: string | null };
    delivery: { last_attempt: string | null; last_sent: string | null };
    counts: { new_articles: number; failed_deliveries: number };
  }> => api.get("/api/v1/admin/pipeline/status").then((r) => r.data),
  triggerIngestion: (): Promise<IngestionResponse> =>
    api.post("/api/v1/admin/ingestion/run").then((r) => r.data),
  triggerDigest: (): Promise<IngestionResponse> =>
    api.post("/api/v1/admin/digest/run").then((r) => r.data),
  triggerCleanup: (): Promise<IngestionResponse> =>
    api.post("/api/v1/admin/cleanup").then((r) => r.data),
};

export function bootstrapAuthFromStorage(): string | null {
  return getStoredToken();
}

export { setStoredToken };
