import { Navigate, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "./AuthContext";

interface ProtectedRouteProps {
  children: ReactNode;
  admin?: boolean;
}

export function ProtectedRoute({ children, admin = false }: ProtectedRouteProps) {
  const { isAuthenticated, isAdmin, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <div
          className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent"
          role="status"
          aria-label="Loading"
        />
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <Navigate
        to={`/login?redirect=${encodeURIComponent(location.pathname + location.search)}`}
        replace
      />
    );
  }

  if (admin && !isAdmin) {
    return (
      <div className="container-page py-16 text-center">
        <h1 className="text-2xl font-semibold text-slate-900">403 — Forbidden</h1>
        <p className="mt-2 text-slate-600">
          You do not have permission to view this page.
        </p>
      </div>
    );
  }

  return <>{children}</>;
}
