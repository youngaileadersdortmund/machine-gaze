export type BoothStage = "idle" | "waiting" | "processing" | "ready" | "deleted";

export type InsightGroup = {
  title: string;
  confidence: "high" | "medium" | "low";
  items: string[];
};

export type DemoSession = {
  id: string;
  participantName: string;
  uploadUrl: string;
  expiresIn: string;
  riskScore: number;
  observed: InsightGroup[];
  speculative: InsightGroup[];
  targeting: string[];
};

export const boothStages: BoothStage[] = [
  "idle",
  "waiting",
  "processing",
  "ready",
  "deleted",
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
    title: "The model is reading visible signals",
    description:
      "The screen shows processing while the backend will eventually run OCR, object detection, and a vision-language report.",
  },
  ready: {
    eyebrow: "Report ready",
    title: "Observed facts versus speculative assumptions",
    description:
      "The demo separates grounded visual observations from lower-confidence profiling claims.",
  },
  deleted: {
    eyebrow: "Session closed",
    title: "Temporary data deleted",
    description:
      "The final production flow should delete the image, generated previews, and temporary report data after finish or expiry.",
  },
};

export const demoSession: DemoSession = {
  id: "MG-42A9",
  participantName: "Mariam",
  uploadUrl: "machinegaze.local/upload/MG-42A9",
  expiresIn: "08:14",
  riskScore: 72,
  observed: [
    {
      title: "Visible scene",
      confidence: "high",
      items: ["one person in frame", "outdoor campus setting", "greenery", "glass building"],
    },
    {
      title: "Detected signals",
      confidence: "medium",
      items: ["formal clothing", "round glasses", "possible badge text", "phone reflection"],
    },
    {
      title: "Privacy exposure",
      confidence: "medium",
      items: ["face visible", "background location clues", "readable text may reveal affiliation"],
    },
  ],
  speculative: [
    {
      title: "Weak profile guesses",
      confidence: "low",
      items: ["student or young professional", "career-focused setting", "prefers organized events"],
    },
    {
      title: "Unsafe overreach",
      confidence: "low",
      items: ["income", "politics", "religion", "sexual orientation", "personality traits"],
    },
  ],
  targeting: [
    "professional clothing",
    "student banking",
    "seminar tickets",
    "productivity tools",
    "travel discounts",
  ],
};

export function getNextStage(stage: BoothStage) {
  const currentIndex = boothStages.indexOf(stage);
  return boothStages[Math.min(currentIndex + 1, boothStages.length - 1)];
}

export function getPreviousStage(stage: BoothStage) {
  const currentIndex = boothStages.indexOf(stage);
  return boothStages[Math.max(currentIndex - 1, 0)];
}
