import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from "axios";
import { ApiError } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export const TOKEN_KEY = "and_access_token";

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string | null): void {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiError>) => {
    if (error.response?.status === 401) {
      setStoredToken(null);
      if (window.location.pathname !== "/login") {
        const current = window.location.pathname + window.location.search;
        window.location.assign(`/login?redirect=${encodeURIComponent(current)}`);
      }
    }
    const detail = error.response?.data?.detail ?? error.message;
    return Promise.reject(new Error(detail));
  },
);
