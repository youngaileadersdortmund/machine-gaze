import type { DemoSession, MachineGuess, TraitReport } from "@/lib/booth-demo";
import type { TraitKey } from "@/lib/backend-api";

const traitOrder: TraitKey[] = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"];

function TraitCard({ trait }: { trait: TraitReport }) {
  return (
    <article className="border-2 border-brand-black bg-white p-4 shadow-[5px_5px_0_#eda913]">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-black text-brand-pink">{trait.name}</h3>
          <p className="mt-2 text-sm font-medium leading-6 text-brand-black/75">{trait.summary}</p>
        </div>
        <p className="shrink-0 border-2 border-brand-black bg-brand-mint px-3 py-1 font-mono text-xl font-black text-brand-black">
          {trait.scorePercent}%
        </p>
      </div>

      <div className="mt-5">
        <div className="h-4 overflow-hidden border-2 border-brand-black bg-brand-cream">
          <div className="h-full bg-brand-orange" style={{ width: `${trait.scorePercent}%` }} />
        </div>
        <div className="mt-2 flex justify-between gap-3 text-xs font-black uppercase text-brand-black/65">
          <span>{trait.lowLabel}</span>
          <span>{trait.highLabel}</span>
        </div>
      </div>
    </article>
  );
}

function GuessRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-t-2 border-brand-black py-3 first:border-t-0 first:pt-0 last:pb-0">
      <p className="text-xs font-black uppercase tracking-[0.14em] text-brand-pink">{label}</p>
      <p className="mt-1 text-sm font-bold leading-6 text-brand-black">{value}</p>
    </div>
  );
}

function MachineGuessPanel({ guess }: { guess: MachineGuess }) {
  return (
    <aside className="border-2 border-brand-black bg-brand-yellow p-5 shadow-[6px_6px_0_#000]">
      <h2 className="text-sm font-black uppercase tracking-[0.18em] text-brand-black">
        The Machine&apos;s Guess
      </h2>
      <div className="mt-4">
        <GuessRow label="Probably studies" value={guess.probablyStudies} />
        <GuessRow label="Campus role" value={guess.campusRole} />
        <GuessRow label="Future forecast" value={guess.futureForecast} />
        <GuessRow label="Classic struggle" value={guess.classicStruggle} />
      </div>
    </aside>
  );
}

export function ResultReport({ session }: { session: DemoSession }) {
  const traitsByKey = new Map(session.traits.map((trait) => [trait.key, trait]));
  const orderedTraits = traitOrder
    .map((key) => traitsByKey.get(key))
    .filter((trait): trait is TraitReport => Boolean(trait));

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_22rem] lg:items-start">
      <section>
        <h2 className="text-sm font-black uppercase tracking-[0.18em] text-brand-pink">
          Big Five read
        </h2>
        <div className="mt-3 grid gap-4">
          {orderedTraits.map((trait) => (
            <TraitCard key={trait.key} trait={trait} />
          ))}
        </div>
      </section>

      {session.machineGuess ? <MachineGuessPanel guess={session.machineGuess} /> : null}
    </div>
  );
}
