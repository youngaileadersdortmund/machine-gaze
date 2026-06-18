export type BackendSessionStatus =
  | "waiting"
  | "uploaded"
  | "processing"
  | "ready"
  | "deleted"
  | "expired"
  | "error";

export type TraitKey =
  | "openness"
  | "conscientiousness"
  | "extraversion"
  | "agreeableness"
  | "neuroticism";

export type TraitReport = {
  key: TraitKey;
  name: string;
  scorePercent: number;
  lowLabel: string;
  highLabel: string;
  summary: string;
};

export type MachineGuess = {
  probablyStudies: string;
  campusRole: string;
  futureForecast: string;
  classicStruggle: string;
};

export type PersonalityReport = {
  traits: TraitReport[];
  machineGuess: MachineGuess;
  model: {
    name: string;
    version: string;
  };
};

export type BackendSession = {
  id: string;
  status: BackendSessionStatus;
  displayName?: string | null;
  expiresAt: string;
  uploadedAt?: string | null;
  processedAt?: string | null;
  errorMessage?: string | null;
  report?: PersonalityReport | null;
};

export type SessionCreateResponse = {
  id: string;
  status: "waiting";
  uploadUrl: string;
  expiresAt: string;
};

export type AdminSessionRow = {
  id: string;
  status: BackendSessionStatus;
  displayName?: string | null;
  createdAt: string;
  expiresAt: string;
  uploadedAt?: string | null;
  processedAt?: string | null;
  errorMessage?: string | null;
};

export type AdminSessionsResponse = {
  sessions: AdminSessionRow[];
};

export type HealthResponse = {
  status: "ok";
  sessions: Record<string, number>;
  jobs: Record<string, number>;
  workerStatus: "offline" | "warming" | "ready" | "error";
  modelId?: string | null;
  modelVersion?: string | null;
  lastSeenAt?: string | null;
  workerErrorMessage?: string | null;
};

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function readError(response: Response) {
  try {
    const payload = await response.json();
    if (typeof payload?.detail === "string") {
      return payload.detail;
    }
    if (typeof payload?.error === "string") {
      return payload.error;
    }
  } catch {
    // Fall back to a generic HTTP message below.
  }

  return `Request failed with status ${response.status}`;
}

export async function requestJson<T>(input: RequestInfo | URL, init?: RequestInit): Promise<T> {
  const response = await fetch(input, {
    ...init,
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(await readError(response), response.status);
  }

  return response.json() as Promise<T>;
}

export async function createSession() {
  return requestJson<SessionCreateResponse>("/api/backend/sessions", { method: "POST" });
}

export async function getSession(sessionId: string) {
  return requestJson<BackendSession>(`/api/backend/sessions/${sessionId}`);
}

export async function finishSession(sessionId: string) {
  return requestJson<{ status: string }>(`/api/backend/sessions/${sessionId}/finish`, {
    method: "POST",
  });
}

export async function uploadSessionPhoto(sessionId: string, token: string, formData: FormData) {
  const params = new URLSearchParams({ token });
  return requestJson<BackendSession>(`/api/backend/sessions/${sessionId}/upload?${params}`, {
    method: "POST",
    body: formData,
  });
}

export async function listAdminSessions() {
  return requestJson<AdminSessionsResponse>("/api/backend/admin/sessions");
}

export async function getHealth() {
  return requestJson<HealthResponse>("/api/backend/health");
}
