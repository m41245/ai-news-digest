import { lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import { PublicLayout } from "./components/layout/PublicLayout";
import { AdminLayout } from "./components/layout/AdminLayout";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { Spinner } from "./components/ui/Spinner";
import { LandingPage } from "./pages/public/LandingPage";
import { NewsPage } from "./pages/public/NewsPage";
import { ArticleDetailPage } from "./pages/public/ArticleDetailPage";
import { DigestsPage } from "./pages/public/DigestsPage";
import { DigestDetailPage } from "./pages/public/DigestDetailPage";
import { CategoriesPage } from "./pages/public/CategoriesPage";
import { PrivacyPolicyPage } from "./pages/public/PrivacyPolicyPage";
import { TermsOfServicePage } from "./pages/public/TermsOfServicePage";
import { NotFoundPage } from "./pages/public/NotFoundPage";
import { LoginPage } from "./pages/auth/LoginPage";
import { RegisterPage } from "./pages/auth/RegisterPage";
import { DashboardPage } from "./pages/dashboard/DashboardPage";

const AdminDashboardPage = lazy(() =>
  import("./pages/admin/AdminDashboardPage").then((m) => ({ default: m.AdminDashboardPage })),
);
const AdminUsersPage = lazy(() =>
  import("./pages/admin/AdminUsersPage").then((m) => ({ default: m.AdminUsersPage })),
);
const AdminSourcesPage = lazy(() =>
  import("./pages/admin/AdminSourcesPage").then((m) => ({ default: m.AdminSourcesPage })),
);
const AdminDigestsPage = lazy(() =>
  import("./pages/admin/AdminDigestsPage").then((m) => ({ default: m.AdminDigestsPage })),
);
const AdminOperationsPage = lazy(() =>
  import("./pages/admin/AdminOperationsPage").then((m) => ({ default: m.AdminOperationsPage })),
);

function PageFallback() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <Spinner label="Loading page" />
    </div>
  );
}

export function App() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <PublicLayout>
            <LoginPage />
          </PublicLayout>
        }
      />
      <Route
        path="/register"
        element={
          <PublicLayout>
            <RegisterPage />
          </PublicLayout>
        }
      />

      <Route
        path="/me"
        element={
          <ProtectedRoute>
            <PublicLayout>
              <DashboardPage />
            </PublicLayout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/admin"
        element={
          <ProtectedRoute admin>
            <AdminLayout>
              <Suspense fallback={<PageFallback />}>
                <AdminDashboardPage />
              </Suspense>
            </AdminLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/users"
        element={
          <ProtectedRoute admin>
            <AdminLayout>
              <Suspense fallback={<PageFallback />}>
                <AdminUsersPage />
              </Suspense>
            </AdminLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/sources"
        element={
          <ProtectedRoute admin>
            <AdminLayout>
              <Suspense fallback={<PageFallback />}>
                <AdminSourcesPage />
              </Suspense>
            </AdminLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/digests"
        element={
          <ProtectedRoute admin>
            <AdminLayout>
              <Suspense fallback={<PageFallback />}>
                <AdminDigestsPage />
              </Suspense>
            </AdminLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/operations"
        element={
          <ProtectedRoute admin>
            <AdminLayout>
              <Suspense fallback={<PageFallback />}>
                <AdminOperationsPage />
              </Suspense>
            </AdminLayout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/"
        element={
          <PublicLayout>
            <LandingPage />
          </PublicLayout>
        }
      />
      <Route
        path="/news"
        element={
          <PublicLayout>
            <NewsPage />
          </PublicLayout>
        }
      />
      <Route
        path="/news/:id"
        element={
          <PublicLayout>
            <ArticleDetailPage />
          </PublicLayout>
        }
      />
      <Route
        path="/digests"
        element={
          <PublicLayout>
            <DigestsPage />
          </PublicLayout>
        }
      />
      <Route
        path="/digests/:id"
        element={
          <PublicLayout>
            <DigestDetailPage />
          </PublicLayout>
        }
      />
      <Route
        path="/categories"
        element={
          <PublicLayout>
            <CategoriesPage />
          </PublicLayout>
        }
      />
      <Route
        path="/privacy"
        element={
          <PublicLayout>
            <PrivacyPolicyPage />
          </PublicLayout>
        }
      />
      <Route
        path="/terms"
        element={
          <PublicLayout>
            <TermsOfServicePage />
          </PublicLayout>
        }
      />

      <Route
        path="*"
        element={
          <PublicLayout>
            <NotFoundPage />
          </PublicLayout>
        }
      />
    </Routes>
  );
}
