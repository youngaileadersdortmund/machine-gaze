const steps = ["Image validation", "OCR scan", "Object detection", "Privacy report"];

export function ProcessingPanel() {
  return (
    <section className="border-2 border-brand-black bg-brand-cream p-5 shadow-[8px_8px_0_#c5227b]">
      <div className="flex items-center gap-4">
        <div className="grid h-16 w-16 place-items-center rounded-full border-2 border-brand-black bg-brand-orange">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-yellow border-t-brand-black" />
        </div>
        <div>
          <p className="text-xl font-black text-brand-pink">Processing image</p>
          <p className="mt-1 text-sm leading-6 text-brand-black/70">
            The GPU worker is running OCR, visual reasoning, and privacy report generation.
          </p>
        </div>
      </div>

      <div className="mt-6 space-y-3">
        {steps.map((step, index) => (
          <div key={step} className="flex items-center gap-3">
            <span
              className={[
                "grid h-8 w-8 place-items-center rounded-full border-2 border-brand-black text-xs font-black",
                index < 2 ? "bg-brand-mint text-brand-black" : "bg-brand-cream text-brand-black/55",
              ].join(" ")}
            >
              {index + 1}
            </span>
            <div className="h-3 flex-1 rounded-full border border-brand-black bg-white">
              <div
                className={[
                  "h-full rounded-full",
                  index < 2 ? "w-full bg-brand-mint" : index === 2 ? "w-2/3 bg-brand-orange" : "w-1/4 bg-brand-yellow",
                ].join(" ")}
              />
            </div>
            <p className="w-36 text-sm font-bold text-brand-black">{step}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
