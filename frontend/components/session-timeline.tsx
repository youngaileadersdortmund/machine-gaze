import type { BoothStage } from "@/lib/booth-demo";
import { boothStages } from "@/lib/booth-demo";

const labels: Record<BoothStage, string> = {
  idle: "Ready",
  waiting: "Scan",
  processing: "Analyze",
  ready: "Report",
  deleted: "Delete",
  expired: "Expired",
  error: "Error",
};

export function SessionTimeline({ stage }: { stage: BoothStage }) {
  const activeIndex = boothStages.indexOf(stage);

  return (
    <ol className="grid grid-cols-7 gap-2">
      {boothStages.map((item, index) => {
        const isActive = index === activeIndex;
        const isComplete = index < activeIndex;

        return (
          <li key={item} className="min-w-0">
            <div
              className={[
                "h-2 rounded-full border border-brand-black",
                isActive
                  ? "bg-brand-pink"
                  : isComplete
                    ? "bg-brand-mint"
                    : "bg-brand-cream",
              ].join(" ")}
            />
            <p
              className={[
                "mt-2 truncate text-xs font-black uppercase",
                isActive ? "text-brand-pink" : "text-brand-black/55",
              ].join(" ")}
            >
              {labels[item]}
            </p>
          </li>
        );
      })}
    </ol>
  );
}
