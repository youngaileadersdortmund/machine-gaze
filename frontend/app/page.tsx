"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { GazeMark } from "@/components/gaze-mark";
import { OperatorControls } from "@/components/operator-controls";
import { PhotoPreview } from "@/components/photo-preview";
import { ProcessingPanel } from "@/components/processing-panel";
import { QrCard } from "@/components/qr-card";
import { ResultReport } from "@/components/result-report";
import { SessionTimeline } from "@/components/session-timeline";
import { StatusPill } from "@/components/status-pill";
import {
  ApiError,
  createSession,
  finishSession,
  getSession,
  type BackendSession,
} from "@/lib/backend-api";
import { getStageFromSession, isTerminalSessionStatus, stageCopy, type BoothStage } from "@/lib/booth-demo";
import { toDisplaySession } from "@/lib/session-mapping";

function messageFromError(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Something went wrong while talking to the backend.";
}

function PrimaryPanel({
  stage,
  session,
  errorMessage,
}: {
  stage: BoothStage;
  session: ReturnType<typeof toDisplaySession> | null;
  errorMessage?: string | null;
}) {
  if (stage === "waiting" && session) {
    return <QrCard session={session} />;
  }

  if (stage === "processing" && session) {
    return (
      <div className="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
        <PhotoPreview participantName={session.participantName} previewUrl={session.previewUrl} />
        <ProcessingPanel />
      </div>
    );
  }

  if (stage === "ready" && session) {
    return (
      <div className="grid gap-5 xl:grid-cols-[0.8fr_1.2fr]">
        <PhotoPreview participantName={session.participantName} previewUrl={session.previewUrl} />
        <ResultReport session={session} />
      </div>
    );
  }

  if (stage === "deleted") {
    return (
      <section className="border-2 border-brand-black bg-brand-black p-8 text-white shadow-[10px_10px_0_#52b49b]">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-black uppercase tracking-[0.18em] text-brand-mint">
            Cleanup complete
          </p>
          <h2 className="mt-4 text-4xl font-black text-white">
            Ready for the next participant
          </h2>
          <p className="mt-4 text-base leading-7 text-white/75">
            The backend confirmed deletion of temporary photo and report data.
          </p>
        </div>
      </section>
    );
  }

  if (stage === "expired" || stage === "error") {
    return (
      <section className="border-2 border-brand-black bg-white p-8 shadow-[10px_10px_0_#eda913]">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-black uppercase tracking-[0.18em] text-brand-pink">
            {stage === "expired" ? "Expired" : "Backend error"}
          </p>
          <h2 className="mt-4 text-4xl font-black text-brand-pink">
            {stage === "expired" ? "This session has closed" : "This session needs a reset"}
          </h2>
          <p className="mt-4 text-base leading-7 text-brand-black/75">
            {errorMessage ||
              (stage === "expired"
                ? "The backend expired the session and removed temporary personal data."
                : "The backend could not complete this session. Start a fresh session for the next participant.")}
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="border-2 border-brand-black bg-brand-mint p-6 shadow-[10px_10px_0_#000] sm:p-8">
      <div className="grid gap-8 lg:grid-cols-[1fr_0.7fr] lg:items-center">
        <div>
          <p className="inline bg-brand-yellow px-2 text-sm font-black uppercase tracking-[0.18em] text-brand-black">
            Visual privacy installation
          </p>
          <h2 className="mt-5 text-5xl font-black leading-none text-brand-pink sm:text-6xl">
            One photo can become a profile.
          </h2>
          <p className="mt-5 max-w-2xl text-base font-medium leading-7 text-brand-black sm:text-lg">
            Start a backend-owned session, show a QR code, process a photo, reveal a
            privacy report, then finish by deleting temporary data.
          </p>
        </div>
        <div className="border-2 border-brand-black bg-brand-cream p-5 shadow-[6px_6px_0_#c5227b]">
          <GazeMark className="mx-auto mb-4 w-36" />
          <p className="text-lg font-black text-brand-pink">Ethical boundary</p>
          <p className="mt-3 text-sm font-medium leading-6 text-brand-black/75">
            Sensitive identity predictions are unsafe speculation, not facts. The purpose
            is privacy literacy, not surveillance.
          </p>
        </div>
      </div>
    </section>
  );
}

export default function Home() {
  const [session, setSession] = useState<BackendSession | null>(null);
  const [uploadUrl, setUploadUrl] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  const stage = getStageFromSession(session);
  const copy = stageCopy[stage];
  const displaySession = useMemo(
    () => (session ? toDisplaySession(session, uploadUrl || undefined) : null),
    [session, uploadUrl],
  );

  const refreshSession = useCallback(async () => {
    if (!session) {
      return;
    }

    try {
      const nextSession = await getSession(session.id);
      setSession(nextSession);
      setErrorMessage(nextSession.errorMessage || null);
    } catch (error) {
      setErrorMessage(messageFromError(error));
    }
  }, [session]);

  useEffect(() => {
    if (!session || isTerminalSessionStatus(session.status)) {
      return;
    }

    const interval = window.setInterval(() => {
      void refreshSession();
    }, 1500);

    return () => window.clearInterval(interval);
  }, [refreshSession, session]);

  async function handleStart() {
    setIsBusy(true);
    setErrorMessage(null);
    try {
      const created = await createSession();
      setUploadUrl(created.uploadUrl);
      setSession({
        id: created.id,
        status: created.status,
        expiresAt: created.expiresAt,
        displayName: null,
        report: null,
      });
    } catch (error) {
      setErrorMessage(messageFromError(error));
    } finally {
      setIsBusy(false);
    }
  }

  async function handleFinish() {
    if (!session) {
      return;
    }

    setIsBusy(true);
    setErrorMessage(null);
    try {
      await finishSession(session.id);
      setSession({
        ...session,
        status: "deleted",
        displayName: null,
        errorMessage: null,
        report: null,
      });
    } catch (error) {
      setErrorMessage(messageFromError(error));
    } finally {
      setIsBusy(false);
    }
  }

  function handleReset() {
    setSession(null);
    setUploadUrl(null);
    setErrorMessage(null);
  }

  const canStart = !session || ["deleted", "expired", "error"].includes(session.status);
  const canFinish = Boolean(session && !["deleted", "expired"].includes(session.status));

  return (
    <main className="min-h-screen overflow-hidden bg-brand-cream text-brand-black">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-6 px-5 py-6 sm:px-8 lg:px-10">
        <header className="relative border-2 border-brand-black bg-white p-5 shadow-[10px_10px_0_#eda913] sm:p-7">
          <div className="grid gap-6 lg:grid-cols-[1fr_17rem] lg:items-end">
            <div>
              <StatusPill stage={stage} label={copy.eyebrow} />
              <h1 className="mt-5 text-6xl font-black leading-none tracking-normal text-brand-pink sm:text-7xl lg:text-8xl">
                {copy.title}
              </h1>
              <p className="mt-5 max-w-3xl text-base font-medium leading-7 text-brand-black sm:text-lg">
                {errorMessage && stage === "idle" ? errorMessage : copy.description}
              </p>
            </div>
            <div className="border-2 border-brand-black bg-brand-mint p-4">
              <GazeMark className="mb-3 w-24" />
              <p className="text-xs font-black uppercase tracking-[0.18em] text-brand-black">
                Booth mode
              </p>
              <p className="mt-2 text-sm font-medium leading-6 text-brand-black/75">
                One participant at a time. Sessions and cleanup are owned by the backend.
              </p>
            </div>
          </div>
          <div className="mt-6">
            <SessionTimeline stage={stage} />
          </div>
        </header>

        <PrimaryPanel stage={stage} session={displaySession} errorMessage={session?.errorMessage || errorMessage} />

        <OperatorControls
          canStart={canStart}
          canFinish={canFinish}
          isBusy={isBusy}
          onStart={handleStart}
          onFinish={handleFinish}
          onReset={handleReset}
        />
      </div>
    </main>
  );
}
