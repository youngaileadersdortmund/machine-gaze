export function PhotoPreview({ participantName }: { participantName: string }) {
  return (
    <section className="border-2 border-brand-black bg-brand-cream p-4 shadow-[8px_8px_0_#eda913]">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-black uppercase tracking-[0.16em] text-brand-pink">
            {participantName}
          </p>
          <p className="mt-1 text-xs font-bold text-brand-black/60">Uploaded photo preview</p>
        </div>
        <span className="rounded-full border-2 border-brand-black bg-brand-mint px-3 py-1 text-xs font-black text-brand-black">
          temporary
        </span>
      </div>

      <div className="relative mt-4 aspect-[4/3] overflow-hidden border-2 border-brand-black bg-brand-black">
        <div className="absolute inset-0 bg-[linear-gradient(135deg,#52b49b_0%,#fffcf9_46%,#eda913_100%)]" />
        <div className="absolute left-6 top-7 h-24 w-24 rounded-full border-[18px] border-brand-pink/80" />
        <div className="absolute right-8 top-8 h-14 w-14 rounded-full bg-brand-yellow" />
        <div className="absolute bottom-0 left-1/2 h-44 w-32 -translate-x-1/2 rounded-t-full bg-brand-black" />
        <div className="absolute bottom-28 left-1/2 h-20 w-20 -translate-x-1/2 rounded-full bg-[#c79372]" />
        <div className="absolute bottom-24 left-1/2 h-6 w-28 -translate-x-1/2 rounded-full bg-brand-cream" />
        <div className="absolute bottom-36 left-1/2 h-3 w-24 -translate-x-1/2 rounded-full border-2 border-brand-black" />
        <div className="absolute left-8 top-8 border-2 border-brand-black bg-brand-cream px-2 py-1 text-xs font-black text-brand-black">
          face
        </div>
        <div className="absolute bottom-10 right-8 border-2 border-brand-black bg-brand-pink px-2 py-1 text-xs font-black text-white">
          clothing
        </div>
        <div className="absolute left-10 top-1/2 border-2 border-brand-black bg-brand-yellow px-2 py-1 text-xs font-black text-brand-black">
          background
        </div>
      </div>
    </section>
  );
}
