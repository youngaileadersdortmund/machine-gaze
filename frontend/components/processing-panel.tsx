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
            Doing some complicated opertations to analyze your awesome personality.
          </p>
        </div>
      </div>
    </section>
  );
}
