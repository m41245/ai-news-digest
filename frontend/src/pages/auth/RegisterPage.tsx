import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { authApi } from "../../api";
import { useAuth } from "../../auth/AuthContext";
import { Seo } from "../../components/Seo";
import { Card } from "../../components/ui/Card";
import { Input } from "../../components/ui/Input";
import { Button } from "../../components/ui/Button";
import { ErrorState } from "../../components/ui/ErrorState";

export function RegisterPage() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated) navigate("/me", { replace: true });
  }, [isAuthenticated, navigate]);

  const mutation = useMutation({
    mutationFn: () => authApi.register({ email, password }),
    onSuccess: () => {
      navigate("/me", { replace: true });
    },
  });

  return (
    <>
      <Seo title="Sign up" noindex />
      <div className="container-page flex min-h-[70vh] items-center justify-center py-12">
        <Card className="w-full max-w-md">
          <div className="mb-6 text-center">
            <h1 className="text-2xl font-bold text-slate-900">Create your account</h1>
            <p className="mt-1 text-sm text-slate-600">
              Sign up to personalize your AI News Digest experience.
            </p>
          </div>

          {(mutation.isError || localError) && (
            <ErrorState
              className="mb-4"
              title="Registration failed"
              message={localError ?? mutation.error?.message ?? "Please try again."}
            />
          )}

          <form
            onSubmit={(e) => {
              e.preventDefault();
              setLocalError(null);
              if (password.length < 8) {
                setLocalError("Password must be at least 8 characters.");
                return;
              }
              if (password !== confirm) {
                setLocalError("Passwords do not match.");
                return;
              }
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
              autoComplete="new-password"
              required
              minLength={8}
              hint="At least 8 characters, with upper, lower, and a digit."
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <Input
              label="Confirm password"
              type="password"
              name="confirm"
              autoComplete="new-password"
              required
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
            />
            <Button type="submit" size="lg" disabled={mutation.isPending}>
              {mutation.isPending ? "Creating account…" : "Create account"}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-600">
            Already have an account?{" "}
            <Link to="/login" className="font-medium text-brand-600 hover:underline">
              Log in
            </Link>
          </p>
        </Card>
      </div>
    </>
  );
}
