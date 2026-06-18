import type { DemoSession, InsightGroup } from "@/lib/booth-demo";

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
            <h3 className="text-base font-black text-brand-black">{group.title}</h3>
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
