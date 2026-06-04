import { GazeMark } from "@/components/gaze-mark";

const sessionRows = [
  {
    id: "MG-42A9",
    name: "Mariam",
    status: "report ready",
    age: "2 min",
  },
  {
    id: "MG-8FD1",
    name: "pending upload",
    status: "waiting",
    age: "6 min",
  },
  {
    id: "MG-013B",
    name: "expired",
    status: "cleanup required",
    age: "15 min",
  },
];

export default function AdminPage() {
  return (
    <main className="min-h-screen bg-brand-cream px-5 py-6 text-brand-black sm:px-8 lg:px-10">
      <div className="mx-auto grid w-full max-w-6xl gap-6">
        <header className="grid gap-5 border-2 border-brand-black bg-white p-6 shadow-[10px_10px_0_#52b49b] md:grid-cols-[1fr_auto] md:items-center">
          <div>
            <p className="text-sm font-black uppercase tracking-[0.18em] text-brand-pink">
              Operator dashboard
            </p>
            <h1 className="mt-4 text-5xl font-black leading-none text-brand-pink">
              Session control
            </h1>
            <p className="mt-3 max-w-3xl text-base font-medium leading-7 text-brand-black/75">
              This placeholder shows the future control surface for approving sessions,
              forcing cleanup, and deciding what appears on the public display.
            </p>
          </div>
          <GazeMark className="w-32" />
        </header>

        <section className="grid gap-4 md:grid-cols-3">
          {["Active sessions", "Pending cleanup", "Worker status"].map((label, index) => (
            <article
              key={label}
              className="border-2 border-brand-black bg-brand-mint p-5 shadow-[5px_5px_0_#000]"
            >
              <p className="text-sm font-black uppercase tracking-[0.14em] text-brand-black">
                {label}
              </p>
              <p className="mt-3 text-4xl font-black text-brand-pink">
                {[2, 1, "online"][index]}
              </p>
            </article>
          ))}
        </section>

        <section className="overflow-hidden border-2 border-brand-black bg-white shadow-[8px_8px_0_#eda913]">
          <div className="border-b-2 border-brand-black bg-brand-black px-5 py-4">
            <h2 className="text-base font-black uppercase tracking-[0.16em] text-white">
              Recent sessions
            </h2>
          </div>
          <div className="divide-y-2 divide-brand-black">
            {sessionRows.map((session) => (
              <div
                key={session.id}
                className="grid gap-3 px-5 py-4 sm:grid-cols-[1fr_1fr_1fr_auto] sm:items-center"
              >
                <p className="font-mono text-sm font-black text-brand-pink">{session.id}</p>
                <p className="text-sm font-medium text-brand-black/75">{session.name}</p>
                <p className="text-sm font-black text-brand-black">{session.status}</p>
                <p className="text-sm font-medium text-brand-black/55">{session.age}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
