"use client";

import { KanbanBoard } from "@/components/KanbanBoard";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();

  // Guard: redirect unauthenticated users to /login
  useEffect(() => {
    const isAuth = typeof window !== "undefined" && sessionStorage.getItem("auth") === "true";
    if (!isAuth) {
      router.replace("/login");
    }
  }, [router]);

  return (
    <>
      <div className="flex justify-end p-4">
        <button
          className="rounded bg-[var(--primary-blue)] px-4 py-2 text-white"
          onClick={() => {
            sessionStorage.removeItem("auth");
            router.replace("/login");
          }}
        >
          Logout
        </button>
      </div>
      <KanbanBoard />
    </>
  );
}
