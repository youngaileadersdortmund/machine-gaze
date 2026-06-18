import type { BackendSession, MachineGuess, TraitReport } from "@/lib/backend-api";

export type BoothStage = "idle" | "waiting" | "processing" | "ready" | "deleted" | "expired" | "error";

export type { MachineGuess, TraitReport };

export type DemoSession = {
  id: string;
  participantName: string;
  uploadUrl: string;
  previewUrl: string | null;
  expiresIn: string;
  traits: TraitReport[];
  machineGuess: MachineGuess | null;
  model: {
    name: string;
    version: string;
  } | null;
};

export const boothStages: BoothStage[] = [
  "idle",
  "waiting",
  "processing",
  "ready",
  "deleted",
  "expired",
  "error",
];

export const stageCopy: Record<
  BoothStage,
  {
    eyebrow: string;
    title: string;
    description: string;
  }
> = {
  idle: {
    eyebrow: "Booth ready",
    title: "Machine Gaze",
    description:
      "Start a private demo session, let one student scan the QR code, then show what AI can observe and what it may over-assume.",
  },
  waiting: {
    eyebrow: "Waiting for upload",
    title: "Scan to join the current session",
    description:
      "The upload link is unique to this booth session and will expire automatically if it is abandoned.",
  },
  processing: {
    eyebrow: "Analysis running",
    title: "Reading the personality signals",
    description:
      "The backend has accepted the photo and the inference worker can now generate a Big Five festival read.",
  },
  ready: {
    eyebrow: "Report ready",
    title: "Persona dossier generated",
    description:
      "The model turned the uploaded image into a stylized machine-read of presentation, mood, and social signals.",
  },
  deleted: {
    eyebrow: "Session closed",
    title: "Temporary data deleted",
    description:
      "The backend confirmed cleanup of the upload, generated report, and temporary session data.",
  },
  expired: {
    eyebrow: "Session expired",
    title: "Temporary data expired",
    description:
      "The upload window closed and the backend removed temporary personal data for this abandoned session.",
  },
  error: {
    eyebrow: "Action needed",
    title: "Session needs attention",
    description:
      "The backend reported an error for this session. Reset the booth view or start a fresh session.",
  },
};

export function getStageFromSession(session: BackendSession | null): BoothStage {
  if (!session) {
    return "idle";
  }

  if (session.status === "uploaded") {
    return "processing";
  }

  return session.status;
}

export function isTerminalSessionStatus(status: BackendSession["status"]) {
  return ["ready", "deleted", "expired", "error"].includes(status);
}
