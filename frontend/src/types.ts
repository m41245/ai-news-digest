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
