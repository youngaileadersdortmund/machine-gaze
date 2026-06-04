export function OperatorControls({
  canGoBack,
  canGoForward,
  onBack,
  onNext,
  onReset,
}: {
  canGoBack: boolean;
  canGoForward: boolean;
  onBack: () => void;
  onNext: () => void;
  onReset: () => void;
}) {
  return (
    <section className="border-2 border-brand-black bg-white p-4 shadow-[6px_6px_0_#52b49b]">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-black uppercase tracking-[0.16em] text-brand-pink">
            Operator controls
          </p>
          <p className="mt-1 text-xs font-medium text-brand-black/65">
            Temporary controls for walking through the booth states before backend wiring.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onBack}
            disabled={!canGoBack}
            className="border-2 border-brand-black bg-brand-cream px-4 py-2 text-sm font-black text-brand-black transition hover:-translate-y-0.5 hover:shadow-[3px_3px_0_#000] disabled:cursor-not-allowed disabled:opacity-40"
          >
            Back
          </button>
          <button
            type="button"
            onClick={onReset}
            className="border-2 border-brand-black bg-white px-4 py-2 text-sm font-black text-brand-black transition hover:-translate-y-0.5 hover:shadow-[3px_3px_0_#000]"
          >
            Reset
          </button>
          <button
            type="button"
            onClick={onNext}
            disabled={!canGoForward}
            className="border-2 border-brand-black bg-brand-orange px-4 py-2 text-sm font-black text-brand-black transition hover:-translate-y-0.5 hover:shadow-[3px_3px_0_#000] disabled:cursor-not-allowed disabled:opacity-40"
          >
            Next state
          </button>
        </div>
      </div>
    </section>
  );
}
