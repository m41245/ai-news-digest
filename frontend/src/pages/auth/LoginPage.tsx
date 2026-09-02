import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { authApi } from "../../api";
import { useAuth } from "../../auth/AuthContext";
import { Seo } from "../../components/Seo";
import { Card } from "../../components/ui/Card";
import { Input } from "../../components/ui/Input";
import { Button } from "../../components/ui/Button";
import { ErrorState } from "../../components/ui/ErrorState";
import { safeRedirect } from "../../utils";

export function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const redirect = safeRedirect(searchParams.get("redirect"));

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  useEffect(() => {
    if (isAuthenticated) navigate(redirect, { replace: true });
  }, [isAuthenticated, navigate, redirect]);

  const mutation = useMutation({
    mutationFn: () => authApi.login({ username: email, password }),
    onSuccess: async () => {
      await login({ username: email, password });
      navigate(redirect, { replace: true });
    },
  });

  return (
    <>
      <Seo title="Log in" noindex />
      <div className="container-page flex min-h-[70vh] items-center justify-center py-12">
        <Card className="w-full max-w-md">
          <div className="mb-6 text-center">
            <h1 className="text-2xl font-bold text-slate-900">Welcome back</h1>
            <p className="mt-1 text-sm text-slate-600">
              Log in to your AI News Digest account.
            </p>
          </div>

          {mutation.isError && (
            <ErrorState
              className="mb-4"
              title="Login failed"
              message={mutation.error?.message ?? "Please try again."}
            />
          )}

          <form
            onSubmit={(e) => {
              e.preventDefault();
              mutation.mutate();
            }}
            className="flex flex-col gap-4"
          >
            <Input
              label="Email"
              type="email"
              name="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <Input
              label="Password"
              type="password"
              name="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <Button type="submit" size="lg" disabled={mutation.isPending}>
              {mutation.isPending ? "Logging in…" : "Log in"}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-600">
            Don&apos;t have an account?{" "}
            <Link to="/register" className="font-medium text-brand-600 hover:underline">
              Sign up
            </Link>
          </p>
        </Card>
      </div>
    </>
  );
}
