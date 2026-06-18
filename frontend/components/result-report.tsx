import type { DemoSession, InsightGroup } from "@/lib/booth-demo";

const confidenceStyles: Record<InsightGroup["confidence"], string> = {
  high: "bg-brand-mint text-brand-black",
  medium: "bg-brand-orange text-brand-black",
  low: "bg-brand-pink text-white",
};

function InsightSection({
  title,
  groups,
}: {
  title: string;
  groups: InsightGroup[];
}) {
  return (
    <section>
      <h2 className="text-sm font-black uppercase tracking-[0.18em] text-brand-pink">
        {title}
      </h2>
      <div className="mt-3 grid gap-3">
        {groups.map((group) => (
          <article key={group.title} className="border-2 border-brand-black bg-white p-4">
            <div className="flex items-start justify-between gap-3">
              <h3 className="text-base font-black text-brand-black">{group.title}</h3>
              <span
                className={`rounded-full border-2 border-brand-black px-2.5 py-1 text-xs font-black ${confidenceStyles[group.confidence]}`}
              >
                {group.confidence}
              </span>
            </div>
            <ul className="mt-3 space-y-2">
              {group.items.map((item) => (
                <li key={item} className="flex gap-2 text-sm leading-6 text-brand-black/75">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-pink" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </article>
        ))}
      </div>
    </section>
  );
}

export function ResultReport({ session }: { session: DemoSession }) {
  return (
    <div className="grid gap-5">
      <section className="border-2 border-brand-black bg-brand-mint p-5 shadow-[8px_8px_0_#000]">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm font-black uppercase tracking-[0.16em] text-brand-black">
              Persona intensity
            </p>
            <p className="mt-1 text-6xl font-black text-brand-pink">{session.riskScore}</p>
          </div>
          <div className="min-w-52 flex-1">
            <div className="h-4 rounded-full border-2 border-brand-black bg-brand-cream">
              <div
                className="h-full rounded-full bg-brand-pink"
                style={{ width: `${session.riskScore}%` }}
              />
            </div>
            <p className="mt-2 text-sm font-medium text-brand-black/70">
              A stylized machine reading, not a psychological diagnosis.
            </p>
          </div>
        </div>
      </section>

      <InsightSection title="Persona read" groups={session.observed} />
      <InsightSection title="Deeper guesses" groups={session.speculative} />

      {session.targeting.length ? (
        <section className="border-2 border-brand-black bg-white p-5 shadow-[6px_6px_0_#eda913]">
          <h2 className="text-sm font-black uppercase tracking-[0.18em] text-brand-pink">
            Influence hooks
          </h2>
          <div className="mt-4 flex flex-wrap gap-2">
            {session.targeting.map((item) => (
              <span
                key={item}
                className="rounded-full border-2 border-brand-black bg-brand-cream px-3 py-1.5 text-sm font-black text-brand-black"
              >
                {item}
              </span>
            ))}
          </div>
        </section>
      ) : null}

      {session.safetyNotes.length ? (
        <section className="border-2 border-brand-black bg-brand-yellow p-5 shadow-[6px_6px_0_#000]">
          <h2 className="text-sm font-black uppercase tracking-[0.18em] text-brand-black">
            Safety notes
          </h2>
          <ul className="mt-3 space-y-2">
            {session.safetyNotes.map((note) => (
              <li key={note} className="flex gap-2 text-sm font-medium leading-6 text-brand-black/80">
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-pink" />
                <span>{note}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {session.model ? (
        <section className="border-2 border-brand-black bg-brand-cream p-4">
          <p className="text-xs font-black uppercase tracking-[0.16em] text-brand-pink">
            Model
          </p>
          <p className="mt-1 break-all font-mono text-sm font-bold text-brand-black">
            {session.model.name} · {session.model.version}
          </p>
        </section>
      ) : null}
    </div>
  );
}
