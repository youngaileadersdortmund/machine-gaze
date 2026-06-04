"use client";

import { useMemo, useState } from "react";

import { GazeMark } from "@/components/gaze-mark";
import { OperatorControls } from "@/components/operator-controls";
import { PhotoPreview } from "@/components/photo-preview";
import { ProcessingPanel } from "@/components/processing-panel";
import { QrCard } from "@/components/qr-card";
import { ResultReport } from "@/components/result-report";
import { SessionTimeline } from "@/components/session-timeline";
import { StatusPill } from "@/components/status-pill";
import {
  boothStages,
  demoSession,
  getNextStage,
  getPreviousStage,
  stageCopy,
  type BoothStage,
} from "@/lib/booth-demo";

function PrimaryPanel({ stage }: { stage: BoothStage }) {
  if (stage === "waiting") {
    return <QrCard session={demoSession} />;
  }

  if (stage === "processing") {
    return (
      <div className="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
        <PhotoPreview participantName={demoSession.participantName} />
        <ProcessingPanel />
      </div>
    );
  }

  if (stage === "ready") {
    return (
      <div className="grid gap-5 xl:grid-cols-[0.8fr_1.2fr]">
        <PhotoPreview participantName={demoSession.participantName} />
        <ResultReport session={demoSession} />
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
            In production, this state should only appear after the backend confirms deletion
            of the upload, generated preview, inference output, and temporary session row.
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
            This first interface models the event booth flow before the real backend and
            GPU worker are connected. Start a session, show a QR code, process a photo,
            reveal a report, then finish by deleting temporary data.
          </p>
        </div>
        <div className="border-2 border-brand-black bg-brand-cream p-5 shadow-[6px_6px_0_#c5227b]">
          <GazeMark className="mx-auto mb-4 w-36" />
          <p className="text-lg font-black text-brand-pink">Ethical boundary</p>
          <p className="mt-3 text-sm font-medium leading-6 text-brand-black/75">
            The final demo should label sensitive identity predictions as unsafe
            speculation, not facts. The purpose is privacy literacy, not surveillance.
          </p>
        </div>
      </div>
    </section>
  );
}

export default function Home() {
  const [stage, setStage] = useState<BoothStage>("idle");
  const copy = stageCopy[stage];

  const stageIndex = useMemo(() => boothStages.indexOf(stage), [stage]);
  const canGoBack = stageIndex > 0;
  const canGoForward = stageIndex < boothStages.length - 1;

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
                {copy.description}
              </p>
            </div>
            <div className="border-2 border-brand-black bg-brand-mint p-4">
              <GazeMark className="mb-3 w-24" />
              <p className="text-xs font-black uppercase tracking-[0.18em] text-brand-black">
                Booth mode
              </p>
              <p className="mt-2 text-sm font-medium leading-6 text-brand-black/75">
                One participant at a time. Backend-owned sessions and auto-expiry will
                replace this local mock state.
              </p>
            </div>
          </div>
          <div className="mt-6">
            <SessionTimeline stage={stage} />
          </div>
        </header>

        <PrimaryPanel stage={stage} />

        <OperatorControls
          canGoBack={canGoBack}
          canGoForward={canGoForward}
          onBack={() => setStage(getPreviousStage(stage))}
          onNext={() => setStage(getNextStage(stage))}
          onReset={() => setStage("idle")}
        />
      </div>
    </main>
  );
}
