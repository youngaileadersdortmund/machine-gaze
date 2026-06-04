import type { BoothStage } from "@/lib/booth-demo";

const stageStyles: Record<BoothStage, string> = {
  idle: "border-brand-pink bg-brand-cream text-brand-pink",
  waiting: "border-brand-mint bg-brand-mint text-brand-black",
  processing: "border-brand-orange bg-brand-orange text-brand-black",
  ready: "border-brand-pink bg-brand-pink text-white",
  deleted: "border-brand-black bg-brand-black text-white",
};

export function StatusPill({
  stage,
  label,
}: {
  stage: BoothStage;
  label: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border-2 px-3 py-1 text-xs font-black uppercase tracking-[0.18em] shadow-[3px_3px_0_#000] ${stageStyles[stage]}`}
    >
      <span className="h-2 w-2 rounded-full bg-current" />
      {label}
    </span>
  );
}
