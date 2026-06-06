"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { GazeMark } from "@/components/gaze-mark";
import {
  ApiError,
  finishSession,
  getHealth,
  listAdminSessions,
  type AdminSessionRow,
  type HealthResponse,
} from "@/lib/backend-api";
import { formatRelativeAge } from "@/lib/session-mapping";

function messageFromError(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Could not reach the backend.";
}

function canFinishStatus(status: AdminSessionRow["status"]) {
  return !["deleted", "expired"].includes(status);
}

export default function AdminPage() {
  const [sessions, setSessions] = useState<AdminSessionRow[]>([]);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [finishingId, setFinishingId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [adminPayload, healthPayload] = await Promise.all([listAdminSessions(), getHealth()]);
      setSessions(adminPayload.sessions);
      setHealth(healthPayload);
      setErrorMessage(null);
    } catch (error) {
      setErrorMessage(messageFromError(error));
    }
  }, []);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void refresh();
    }, 0);
    const interval = window.setInterval(() => {
      void refresh();
    }, 3000);
    return () => {
      window.clearTimeout(timeout);
      window.clearInterval(interval);
    };
  }, [refresh]);

  const counts = useMemo(() => {
    const active = sessions.filter((session) =>
      ["waiting", "uploaded", "processing", "ready"].includes(session.status),
    ).length;
    const cleanup = sessions.filter((session) => ["expired", "error"].includes(session.status)).length;
    const worker = health?.workerStatus || "offline";
    return [active, cleanup, worker];
  }, [health, sessions]);

  async function handleFinish(sessionId: string) {
    setFinishingId(sessionId);
    try {
      await finishSession(sessionId);
      await refresh();
    } catch (error) {
      setErrorMessage(messageFromError(error));
    } finally {
      setFinishingId(null);
    }
  }

  return (
    <main className="min-h-screen bg-brand-cream px-5 py-6 text-brand-black sm:px-8 lg:px-10">
      <div className="mx-auto grid w-full max-w-6xl gap-6">
        <header className="grid gap-5 border-2 border-brand-black bg-white p-6 shadow-[10px_10px_0_#52b49b] md:grid-cols-[1fr_auto] md:items-center">
          <div>
            <p className="text-sm font-black uppercase tracking-[0.18em] text-brand-pink">
              Operator dashboard
            </p>
            <h1 className="mt-4 text-5xl font-black leading-none text-brand-pink">
              Session control
            </h1>
            <p className="mt-3 max-w-3xl text-base font-medium leading-7 text-brand-black/75">
              Live backend sessions, worker queue status, and cleanup controls for the booth.
            </p>
          </div>
          <GazeMark className="w-32" />
        </header>

        {errorMessage ? (
          <section className="border-2 border-brand-black bg-brand-yellow px-5 py-3 text-sm font-black text-brand-black shadow-[5px_5px_0_#000]">
            {errorMessage}
          </section>
        ) : null}

        <section className="grid gap-4 md:grid-cols-3">
          {["Active sessions", "Pending cleanup", "Worker status"].map((label, index) => (
            <article
              key={label}
              className="border-2 border-brand-black bg-brand-mint p-5 shadow-[5px_5px_0_#000]"
            >
              <p className="text-sm font-black uppercase tracking-[0.14em] text-brand-black">
                {label}
              </p>
              <p className="mt-3 text-4xl font-black text-brand-pink">{counts[index]}</p>
              {label === "Worker status" ? (
                <p className="mt-2 break-all text-xs font-bold leading-5 text-brand-black/70">
                  {health?.modelId || "no model heartbeat yet"}
                </p>
              ) : null}
            </article>
          ))}
        </section>

        {health?.workerErrorMessage ? (
          <section className="border-2 border-brand-black bg-white px-5 py-3 text-sm font-bold text-brand-pink shadow-[5px_5px_0_#eda913]">
            {health.workerErrorMessage}
          </section>
        ) : null}

        <section className="overflow-hidden border-2 border-brand-black bg-white shadow-[8px_8px_0_#eda913]">
          <div className="border-b-2 border-brand-black bg-brand-black px-5 py-4">
            <h2 className="text-base font-black uppercase tracking-[0.16em] text-white">
              Recent sessions
            </h2>
          </div>
          <div className="divide-y-2 divide-brand-black">
            {sessions.length ? (
              sessions.map((session) => (
                <div
                  key={session.id}
                  className="grid gap-3 px-5 py-4 sm:grid-cols-[1fr_1fr_1fr_1fr_auto] sm:items-center"
                >
                  <p className="font-mono text-sm font-black text-brand-pink">{session.id}</p>
                  <p className="text-sm font-medium text-brand-black/75">
                    {session.displayName || "pending upload"}
                  </p>
                  <p className="text-sm font-black text-brand-black">{session.status}</p>
                  <p className="text-sm font-medium text-brand-black/55">
                    {formatRelativeAge(session.createdAt)}
                  </p>
                  <button
                    type="button"
                    onClick={() => void handleFinish(session.id)}
                    disabled={!canFinishStatus(session.status) || finishingId === session.id}
                    className="border-2 border-brand-black bg-brand-orange px-3 py-2 text-xs font-black text-brand-black transition hover:-translate-y-0.5 hover:shadow-[3px_3px_0_#000] disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {finishingId === session.id ? "Deleting" : "Finish"}
                  </button>
                </div>
              ))
            ) : (
              <p className="px-5 py-6 text-sm font-medium text-brand-black/65">
                No sessions have been created yet.
              </p>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
