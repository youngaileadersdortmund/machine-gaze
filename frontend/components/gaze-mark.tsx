const segments = [
  "bg-brand-mint",
  "bg-brand-mint",
  "bg-brand-yellow",
  "bg-brand-orange",
  "bg-brand-orange",
  "bg-brand-pink",
  "bg-brand-pink",
  "bg-brand-mint",
  "bg-brand-mint",
  "bg-brand-yellow",
  "bg-brand-orange",
  "bg-brand-pink",
];

export function GazeMark({ className = "" }: { className?: string }) {
  return (
    <div className={`relative aspect-square ${className}`} aria-hidden="true">
      {segments.map((color, index) => (
        <span
          key={`${color}-${index}`}
          className={`absolute left-1/2 top-1/2 h-[16%] w-[6%] origin-[50%_310%] rounded-full border border-brand-black ${color}`}
          style={{ transform: `translate(-50%, -310%) rotate(${index * 30}deg)` }}
        />
      ))}
      <div className="absolute left-1/2 top-1/2 h-[58%] w-[58%] -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-brand-black bg-brand-cream" />
      <div className="absolute left-1/2 top-1/2 h-[22%] w-[22%] -translate-x-1/2 -translate-y-1/2 rounded-full bg-brand-black" />
    </div>
  );
}
