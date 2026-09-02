import React from "react";
import { NavLink, Link } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { Button } from "../ui/Button";
import { cn } from "../../utils";

const ADMIN_LINKS = [
  { to: "/admin", label: "Dashboard", end: true },
  { to: "/admin/users", label: "Users" },
  { to: "/admin/sources", label: "Sources" },
  { to: "/admin/digests", label: "Digests" },
  { to: "/admin/operations", label: "Operations" },
];

export function AdminLayout({ children }: { children: React.ReactNode }) {
  const { logout, user } = useAuth();

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/80 backdrop-blur">
        <div className="container-page flex h-16 items-center justify-between">
          <Link to="/admin" className="flex items-center gap-2 text-lg font-bold text-slate-900">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-sm font-bold text-white">
              N
            </span>
            <span className="hidden sm:inline">Admin</span>
          </Link>
          <div className="flex items-center gap-2">
            <Link to="/" className="text-sm text-slate-500 hover:text-slate-900">
              View site
            </Link>
            <span className="text-slate-300">|</span>
            <span className="text-sm text-slate-600">{user?.email}</span>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                logout();
                window.location.assign("/");
              }}
            >
              Log out
            </Button>
          </div>
        </div>
      </header>
      <div className="flex flex-1">
        <aside className="hidden w-56 shrink-0 border-r border-slate-200 bg-white px-3 py-6 md:block">
          <nav aria-label="Admin" className="flex flex-col gap-1">
            {ADMIN_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.end}
                className={({ isActive }) =>
                  cn(
                    "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-brand-50 text-brand-700"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
                  )
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
        </aside>
        <main id="main-content" className="flex-1" tabIndex={-1}>
          <div className="container-page py-8">{children}</div>
        </main>
      </div>
    </div>
  );
}
