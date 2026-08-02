"use client";

import { useState, useEffect, type FormEvent } from "react";
import { useRouter } from "next/navigation";

/**
 * Login page with hard-coded credentials (user / password).
 * On successful login we store an auth flag in sessionStorage
 * and redirect to the main Kanban board.
 */
export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // If already authenticated, redirect to home
  useEffect(() => {
    if (typeof window !== "undefined" && sessionStorage.getItem("auth") === "true") {
      router.replace("/");
    }
  }, [router]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    // Hard-coded credentials as per project spec
    if (username === "user" && password === "password") {
      sessionStorage.setItem("auth", "true");
      router.replace("/");
    } else {
      setError("Invalid credentials");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-[var(--purple-secondary)] via-[var(--navy-dark)] to-[var(--primary-blue)] p-6">
      <form
        onSubmit={handleSubmit}
        data-testid="login-form"
        className="w-full max-w-sm rounded-3xl border border-white/10 bg-white p-8 shadow-[var(--shadow)]"
      >
        <div className="text-center">
          <span className="mx-auto mb-3 block h-2.5 w-10 rounded-full bg-[var(--accent-yellow)]" />
          <h2 className="font-display text-2xl font-semibold text-[var(--navy-dark)]">
            Project Manager
          </h2>
          <p className="mt-1 text-sm text-[var(--gray-text)]">Sign in to your project board</p>
        </div>

        <div className="mb-4 mt-6">
          <label className="block text-sm font-medium text-[var(--navy-dark)]" htmlFor="username">
            Username
          </label>
          <input
            id="username"
            type="text"
            placeholder="user"
            value={username}
            onChange={(e) => {
              setUsername(e.target.value);
              if (error) setError(null);
            }}
            className="mt-1 w-full rounded-lg border border-[var(--stroke)] px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
            data-testid="username-input"
          />
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium text-[var(--navy-dark)]" htmlFor="password">
            Password
          </label>
          <div className="relative mt-1">
            <input
              id="password"
              type={showPassword ? "text" : "password"}
              placeholder="password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                if (error) setError(null);
              }}
              className="w-full rounded-lg border border-[var(--stroke)] px-3 py-2 pr-14 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
              data-testid="password-input"
            />
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              aria-label={showPassword ? "Hide password" : "Show password"}
              className="absolute inset-y-0 right-1 my-auto h-8 rounded-md px-2 text-xs font-semibold text-[var(--secondary-purple)] hover:bg-[var(--surface)]"
            >
              {showPassword ? "Hide" : "Show"}
            </button>
          </div>
        </div>

        {error && (
          <p
            className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
            data-testid="error-msg"
          >
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={!username.trim() || !password}
          className="w-full rounded-full bg-[var(--secondary-purple)] py-2.5 font-semibold text-white transition hover:opacity-90 disabled:opacity-40"
          data-testid="login-button"
        >
          Sign In
        </button>

        <p className="mt-4 text-center text-xs text-[var(--gray-text)]">
          Demo login: <span className="font-semibold text-[var(--navy-dark)]">user</span> /{" "}
          <span className="font-semibold text-[var(--navy-dark)]">password</span>
        </p>
      </form>
    </div>
  );
}