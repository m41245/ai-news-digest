import { api, getStoredToken, setStoredToken } from "./client";
import type {
  AdminUser,
  AdminUserUpdateRequest,
  Article,
  Category,
  Company,
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
  PersonalizedFeedResponse,
  PersonalizedTrendResponse,
  PublicDigest,
  PublicStoryCluster,
  PublicStoryClusterSearch,
  PublicTrendSearch,
  RecommendationResponse,
  RegisterRequest,
  RelatedStoryResponse,
  Source,
  SourceCreateRequest,
  SourceUpdateRequest,
  StoryIntelligenceBriefResponse,
  StoryTimelineResponse,
  SystemStats,
  Topic,
  Trend,
  User,
  UserPreferenceResponse,
  UserPreferenceUpdateRequest,
  UserUpdateRequest,
  EvaluationRun,
  EvaluationDetailResponse,
  QualitySnapshot,
  QualityHealthResponse,
  DriftSignal,
  TriggerEvaluationResponse,
  QualityGateResultResponse,
  IntelligenceHealthResponse,
  OperationalAlertResponse,
  QualityGateDefinitionResponse,
  TriggerQualityGateEvaluationResponse,
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
    company_id?: string;
    topic_id?: string;
    min_importance?: number;
    published_from?: string;
    published_to?: string;
    search?: string;
    mode?: "lexical" | "semantic" | "hybrid";
  } = {}): Promise<PaginatedResponse<Article>> =>
    api.get("/api/v1/public/articles", { params }).then((r) => r.data),
  article: (id: string): Promise<Article> =>
    api.get(`/api/v1/public/articles/${id}`).then((r) => r.data),
  relatedStories: (id: string, limit = 10): Promise<RelatedStoryResponse[]> =>
    api
      .get(`/api/v1/public/articles/${id}/related`, { params: { limit } })
      .then((r) => r.data),
  digests: (params: { limit?: number; offset?: number } = {}): Promise<
    PaginatedResponse<PublicDigest>
  > => api.get("/api/v1/public/digests", { params }).then((r) => r.data),
  digest: (id: string): Promise<PublicDigest> =>
    api.get(`/api/v1/public/digests/${id}`).then((r) => r.data),
  categories: (): Promise<Category[]> =>
    api.get("/api/v1/public/categories").then((r) => r.data),
  sources: (): Promise<Source[]> =>
    api.get("/api/v1/public/sources").then((r) => r.data),
  companies: (): Promise<Company[]> =>
    api.get("/api/v1/public/companies").then((r) => r.data),
  topics: (): Promise<Topic[]> =>
    api.get("/api/v1/public/topics").then((r) => r.data),
  topStory: (): Promise<{
    top_story_cluster_id: string | null;
    top_story_score: number | null;
    total_candidates: number;
    eligible_candidates: number;
    ranking_window_start: string | null;
    ranking_window_end: string | null;
    generated_at: string;
    title: string | null;
    slug: string | null;
    summary: string | null;
    importance_score: number | null;
    confidence: number | null;
    activity_status?: string | null;
    activity_score?: number | null;
  }> => api.get("/api/v1/public/story-ranking/top-story").then((r) => r.data),
  storyCluster: (slug: string): Promise<PublicStoryCluster> =>
    api.get(`/api/v1/public/story-clusters/${encodeURIComponent(slug)}`).then((r) => r.data),
  storyClusterBrief: (slug: string): Promise<StoryIntelligenceBriefResponse> =>
    api.get(`/api/v1/public/story-clusters/${encodeURIComponent(slug)}/brief`).then((r) => r.data),
  storyTimeline: (clusterId: string): Promise<StoryTimelineResponse> =>
    api.get(`/api/v1/public/story-clusters/${clusterId}/timeline`).then((r) => r.data),
  storyClusters: (params: {
    limit?: number;
    offset?: number;
    search?: string;
    category_id?: string;
    company_id?: string;
    topic_id?: string;
    published_from?: string;
    published_to?: string;
    min_importance?: number;
  } = {}): Promise<PaginatedResponse<PublicStoryClusterSearch>> =>
    api.get("/api/v1/public/story-clusters", { params }).then((r) => r.data),
  entityRelationships: (entityType: string, entityId: string, limit = 50): Promise<{
    entity_type: string;
    entity_id: string;
    relationships: Array<{
      id: string;
      subject_entity_type: string;
      subject_entity_id: string;
      relationship_type: string;
      object_entity_type: string;
      object_entity_id: string;
      status: string;
      confidence?: number | null;
      provenance_source?: string | null;
      observed_at?: string | null;
    }>;
  }> =>
    api
      .get(`/api/v1/public/relationships/entities/${encodeURIComponent(entityType)}/${encodeURIComponent(entityId)}`, {
        params: { limit },
      })
      .then((r) => r.data),
  storyClusterRelationships: (clusterId: string): Promise<{
    cluster_id: string;
    related_companies: string[];
    related_topics: string[];
    relationship_count: number;
  }> =>
    api
      .get(`/api/v1/public/relationships/story-clusters/${encodeURIComponent(clusterId)}`)
      .then((r) => r.data),
  trends: (params: {
    limit?: number;
    offset?: number;
    trend_type?: string;
    status?: string;
    min_score?: number;
  } = {}): Promise<PaginatedResponse<PublicTrendSearch>> =>
    api.get("/api/v1/public/trends", { params }).then((r) => r.data),
  trend: (id: string): Promise<Trend> =>
    api.get(`/api/v1/public/trends/${id}`).then((r) => r.data),
  search: (q: string, limit = 20): Promise<PaginatedResponse<Article>> =>
    api
      .get("/api/v1/public/articles", { params: { search: q, limit } })
      .then((r) => r.data),
  graphConnections: (entityType: string, entityId: string, limit = 20, offset = 0): Promise<{
    entity_type: string;
    entity_id: string;
    connections: Array<{
      entity_type: string;
      entity_id: string;
      name: string;
      relationship_type?: string | null;
      status?: string | null;
      score: number;
      signals: string[];
      explanation: string;
      source_count: number;
      is_disputed: boolean;
      is_retracted: boolean;
    }>;
    total: number;
    limit: number;
    offset: number;
    truncated: boolean;
  }> =>
    api
      .get(`/api/v1/public/graph/entities/${encodeURIComponent(entityType)}/${encodeURIComponent(entityId)}/connections`, {
        params: { limit, offset },
      })
      .then((r) => r.data),
  entityTemporalConnections: (entityType: string, entityId: string, limit = 20, offset = 0): Promise<{
    entity_type: string;
    entity_id: string;
    connections: Array<{
      entity_type: string;
      entity_id: string;
      name: string;
      relationship_type?: string | null;
      status?: string | null;
      score: number;
      signals: string[];
      explanation: string;
      source_count: number;
      is_disputed: boolean;
      is_retracted: boolean;
      first_observed_at?: string | null;
      last_observed_at?: string | null;
      observation_count: number;
      activity_status?: string | null;
      activity_score: number;
    }>;
    total: number;
    limit: number;
    offset: number;
    truncated: boolean;
  }> =>
    api
      .get(`/api/v1/public/graph/entities/${encodeURIComponent(entityType)}/${encodeURIComponent(entityId)}/temporal-connections`, {
        params: { limit, offset },
      })
      .then((r) => r.data),
  entityEvolution: (entityType: string, entityId: string): Promise<{
    entity_type: string;
    entity_id: string;
    new_connections: Array<Record<string, unknown>>;
    recently_active: Array<Record<string, unknown>>;
    recently_changed: Array<Record<string, unknown>>;
    historical_connections: Array<Record<string, unknown>>;
    total_connections: number;
    generated_at: string;
  }> =>
    api
      .get(`/api/v1/public/graph/entities/${encodeURIComponent(entityType)}/${encodeURIComponent(entityId)}/evolution`)
      .then((r) => r.data),
  entityRelationshipHistory: (entityType: string, entityId: string, limit = 50): Promise<{
    entity_type: string;
    entity_id: string;
    history: Array<Record<string, unknown>>;
    total: number;
    limit: number;
  }> =>
    api
      .get(`/api/v1/public/relationships/entities/${encodeURIComponent(entityType)}/${encodeURIComponent(entityId)}/history`, {
        params: { limit },
      })
      .then((r) => r.data),
  entityRelationshipChanges: (entityType: string, entityId: string, limit = 50): Promise<Array<{
    change_type: string;
    relationship_type: string;
    object_entity_type: string;
    object_entity_id: string;
    object_name: string;
    observed_at?: string | null;
    explanation: string;
  }>> =>
    api
      .get(`/api/v1/public/graph/entities/${encodeURIComponent(entityType)}/${encodeURIComponent(entityId)}/changes`, {
        params: { limit },
      })
      .then((r) => r.data),
  storyClusterGraphConnections: (clusterId: string, limit = 20, offset = 0): Promise<{
    entity_type: string;
    entity_id: string;
    connections: Array<{
      entity_type: string;
      entity_id: string;
      name: string;
      relationship_type?: string | null;
      status?: string | null;
      score: number;
      signals: string[];
      explanation: string;
      source_count: number;
      is_disputed: boolean;
      is_retracted: boolean;
    }>;
    total: number;
    limit: number;
    offset: number;
    truncated: boolean;
  }> =>
    api
      .get(`/api/v1/public/graph/story-clusters/${encodeURIComponent(clusterId)}/connections`, {
        params: { limit, offset },
      })
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
  triggerArticleAnalysis: (articleId: string): Promise<{ message: string; task_id: string }> =>
    api.post(`/api/v1/admin/articles/${articleId}/analyze`).then((r) => r.data),
  triggerPendingAnalysis: (): Promise<{ message: string; task_id: string }> =>
    api.post("/api/v1/admin/articles/analyze-pending").then((r) => r.data),
  evaluation: {
    listRuns: (params: { limit?: number; offset?: number; evaluation_type?: string; status?: string; scope?: string; provider?: string } = {}): Promise<PaginatedResponse<EvaluationRun>> =>
      api.get("/api/v1/admin/intelligence/evaluations", { params }).then((r) => r.data),
    getRun: (runId: string): Promise<EvaluationDetailResponse> =>
      api.get(`/api/v1/admin/intelligence/evaluations/${runId}`).then((r) => r.data),
    listSnapshots: (params: { limit?: number; offset?: number; scope?: string } = {}): Promise<PaginatedResponse<QualitySnapshot>> =>
      api.get("/api/v1/admin/intelligence/quality/snapshots", { params }).then((r) => r.data),
    getHealth: (scope: string = "global"): Promise<QualityHealthResponse> =>
      api.get("/api/v1/admin/intelligence/quality/health", { params: { scope } }).then((r) => r.data),
    getDrift: (scope: string = "global", provider?: string): Promise<DriftSignal[]> =>
      api.get("/api/v1/admin/intelligence/drift", { params: { scope, provider } }).then((r) => r.data),
    trigger: (evaluation_type: string = "manual", scope: string = "global"): Promise<TriggerEvaluationResponse> =>
      api.post("/api/v1/admin/intelligence/evaluations/run", null, { params: { evaluation_type, scope } }).then((r) => r.data),
    getIntelligenceHealth: (scope: string = "global"): Promise<IntelligenceHealthResponse> =>
      api.get("/api/v1/admin/intelligence/health", { params: { scope } }).then((r) => r.data),
    listGateResults: (params: { limit?: number; offset?: number; component?: string; result?: string } = {}): Promise<PaginatedResponse<QualityGateResultResponse>> =>
      api.get("/api/v1/admin/intelligence/gates", { params }).then((r) => r.data),
    listGateDefinitions: (): Promise<QualityGateDefinitionResponse[]> =>
      api.get("/api/v1/admin/intelligence/gates/definitions").then((r) => r.data),
    listAlerts: (params: { limit?: number; offset?: number; component?: string; severity?: string; resolved?: boolean } = {}): Promise<PaginatedResponse<OperationalAlertResponse>> =>
      api.get("/api/v1/admin/intelligence/alerts", { params }).then((r) => r.data),
    resolveAlert: (alertId: string): Promise<OperationalAlertResponse> =>
      api.post(`/api/v1/admin/intelligence/alerts/${alertId}/resolve`).then((r) => r.data),
    triggerGateEvaluation: (): Promise<TriggerQualityGateEvaluationResponse> =>
      api.post("/api/v1/admin/intelligence/gates/evaluate", null).then((r) => r.data),
  },
};

export function bootstrapAuthFromStorage(): string | null {
  return getStoredToken();
}

export const userPreferenceApi = {
  get: (): Promise<UserPreferenceResponse> =>
    api.get("/api/v1/me/preferences").then((r) => r.data),
  update: (data: UserPreferenceUpdateRequest): Promise<UserPreferenceResponse> =>
    api.put("/api/v1/me/preferences", data).then((r) => r.data),
  reset: (): Promise<void> =>
    api.post("/api/v1/me/preferences/reset").then((r) => r.data),
  followCompany: (slug: string): Promise<void> =>
    api.post(`/api/v1/me/preferences/companies/${encodeURIComponent(slug)}`).then((r) => r.data),
  unfollowCompany: (slug: string): Promise<void> =>
    api.delete(`/api/v1/me/preferences/companies/${encodeURIComponent(slug)}`).then((r) => r.data),
  followTopic: (slug: string): Promise<void> =>
    api.post(`/api/v1/me/preferences/topics/${encodeURIComponent(slug)}`).then((r) => r.data),
  unfollowTopic: (slug: string): Promise<void> =>
    api.delete(`/api/v1/me/preferences/topics/${encodeURIComponent(slug)}`).then((r) => r.data),
  followCategory: (id: string): Promise<void> =>
    api.post(`/api/v1/me/preferences/categories/${encodeURIComponent(id)}`).then((r) => r.data),
  unfollowCategory: (id: string): Promise<void> =>
    api.delete(`/api/v1/me/preferences/categories/${encodeURIComponent(id)}`).then((r) => r.data),
  followSource: (id: string): Promise<void> =>
    api.post(`/api/v1/me/preferences/sources/${encodeURIComponent(id)}`).then((r) => r.data),
  unfollowSource: (id: string): Promise<void> =>
    api.delete(`/api/v1/me/preferences/sources/${encodeURIComponent(id)}`).then((r) => r.data),
  muteCompany: (slug: string): Promise<void> =>
    api.post(`/api/v1/me/preferences/muted/companies/${encodeURIComponent(slug)}`).then((r) => r.data),
  unmuteCompany: (slug: string): Promise<void> =>
    api.delete(`/api/v1/me/preferences/muted/companies/${encodeURIComponent(slug)}`).then((r) => r.data),
  muteTopic: (slug: string): Promise<void> =>
    api.post(`/api/v1/me/preferences/muted/topics/${encodeURIComponent(slug)}`).then((r) => r.data),
  unmuteTopic: (slug: string): Promise<void> =>
    api.delete(`/api/v1/me/preferences/muted/topics/${encodeURIComponent(slug)}`).then((r) => r.data),
  muteCategory: (id: string): Promise<void> =>
    api.post(`/api/v1/me/preferences/muted/categories/${encodeURIComponent(id)}`).then((r) => r.data),
  unmuteCategory: (id: string): Promise<void> =>
    api.delete(`/api/v1/me/preferences/muted/categories/${encodeURIComponent(id)}`).then((r) => r.data),
  muteSource: (id: string): Promise<void> =>
    api.post(`/api/v1/me/preferences/muted/sources/${encodeURIComponent(id)}`).then((r) => r.data),
  unmuteSource: (id: string): Promise<void> =>
    api.delete(`/api/v1/me/preferences/muted/sources/${encodeURIComponent(id)}`).then((r) => r.data),
};

export const personalizedApi = {
  feed: (params: {
    page?: number;
    page_size?: number;
    sort?: string;
    min_importance?: number;
    min_confidence?: number;
  } = {}): Promise<PersonalizedFeedResponse> =>
    api.get("/api/v1/me/feed", { params }).then((r) => r.data),
  trends: (params: {
    page?: number;
    page_size?: number;
  } = {}): Promise<PersonalizedTrendResponse[]> =>
    api.get("/api/v1/me/trends", { params }).then((r) => r.data),
  recommendations: (params: {
    page?: number;
    page_size?: number;
    sort?: string;
  } = {}): Promise<RecommendationResponse> =>
    api.get("/api/v1/me/recommendations", { params }).then((r) => r.data),
};

export { setStoredToken };
