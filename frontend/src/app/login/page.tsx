"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * Simple login page with hard‑coded credentials (user / password).
 * On successful login we store an auth flag in sessionStorage and
 * redirect to the main Kanban board.
 */
export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  // If already authenticated, redirect to home
  useEffect(() => {
    if (typeof window !== "undefined" && sessionStorage.getItem("auth") === "true") {
      router.replace("/");
    }
  }, [router]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Hard‑coded credentials as per project spec
    if (username === "user" && password === "password") {
      sessionStorage.setItem("auth", "true");
      router.replace("/");
    } else {
      setError("Invalid credentials");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-100">
      <form
        onSubmit={handleSubmit}
        className="rounded bg-white p-8 shadow-md"
        data-testid="login-form"
      >
        <h2 className="mb-4 text-center text-2xl font-semibold">Login</h2>
        <div className="mb-4">
          <label className="block text-sm font-medium" htmlFor="username">
            Username
          </label>
          <input
            id="username"
            type="text"
            placeholder="user"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="mt-1 w-full rounded border px-3 py-2"
            data-testid="username-input"
          />
        </div>
        <div className="mb-4">
          <label className="block text-sm font-medium" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            type="password"
            placeholder="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded border px-3 py-2"
            data-testid="password-input"
          />
        </div>
        {error && <p className="mb-4 text-red-600" data-testid="error-msg">{error}</p>}
        <button
          type="submit"
          className="w-full rounded bg-[var(--primary-blue)] py-2 text-white"
          data-testid="login-button"
        >
          Sign In
        </button>
      </form>
    </div>
  );
}
