import type { BackendSession } from "@/lib/backend-api";
import type { DemoSession } from "@/lib/booth-demo";

function parseBackendTime(value: string) {
  const hasTimezone = /(?:z|[+-]\d\d:?\d\d)$/i.test(value);
  return new Date(hasTimezone ? value : `${value}Z`).getTime();
}

function formatRemaining(expiresAt: string) {
  const remainingMs = parseBackendTime(expiresAt) - Date.now();
  if (!Number.isFinite(remainingMs) || remainingMs <= 0) {
    return "00:00";
  }

  const totalSeconds = Math.floor(remainingMs / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
}

export function toDisplaySession(session: BackendSession, uploadUrl?: string): DemoSession {
  return {
    id: session.id,
    participantName: session.displayName || "Current participant",
    uploadUrl: uploadUrl || `/upload/${session.id}`,
    expiresIn: formatRemaining(session.expiresAt),
    riskScore: session.report?.riskScore ?? 0,
    observed: session.report?.observed ?? [],
    speculative: session.report?.speculative ?? [],
    targeting: session.report?.targeting ?? [],
    safetyNotes: session.report?.safetyNotes ?? [],
    model: session.report?.model ?? null,
  };
}

export function formatRelativeAge(value: string) {
  const timestamp = parseBackendTime(value);
  const deltaMs = Date.now() - timestamp;
  if (!Number.isFinite(timestamp) || deltaMs < 0) {
    return "now";
  }

  const minutes = Math.floor(deltaMs / 60000);
  if (minutes < 1) {
    return "now";
  }
  if (minutes === 1) {
    return "1 min";
  }
  return `${minutes} min`;
}
