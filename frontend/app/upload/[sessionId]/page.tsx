import { GazeMark } from "@/components/gaze-mark";

export default async function UploadPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await params;

  return (
    <main className="min-h-screen bg-brand-cream px-5 py-6 text-brand-black">
      <div className="mx-auto grid min-h-[calc(100vh-3rem)] w-full max-w-xl content-center gap-5">
        <section className="border-2 border-brand-black bg-brand-mint p-6 shadow-[8px_8px_0_#000]">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-black uppercase tracking-[0.18em] text-brand-black">
                Machine Gaze
              </p>
              <h1 className="mt-4 text-4xl font-black leading-none text-brand-pink">
                Add your photo to the booth
              </h1>
            </div>
            <GazeMark className="w-20 shrink-0" />
          </div>
          <p className="mt-4 text-sm font-medium leading-6 text-brand-black/75">
            This mobile page is a static placeholder. Later it will upload the image to
            FastAPI and attach it to this session.
          </p>
          <p className="mt-4 bg-brand-yellow px-3 py-2 font-mono text-sm font-black text-brand-black">
            {sessionId}
          </p>
        </section>

        <form className="grid gap-4 border-2 border-brand-black bg-white p-6 shadow-[8px_8px_0_#c5227b]">
          <label className="grid gap-2">
            <span className="text-sm font-black uppercase tracking-[0.12em] text-brand-pink">
              Display name
            </span>
            <input
              type="text"
              placeholder="Use a nickname"
              className="border-2 border-brand-black bg-brand-cream px-3 py-3 text-base font-medium text-brand-black outline-none transition focus:shadow-[4px_4px_0_#eda913]"
            />
          </label>

          <label className="grid gap-2">
            <span className="text-sm font-black uppercase tracking-[0.12em] text-brand-pink">
              Photo
            </span>
            <input
              type="file"
              accept="image/*"
              className="border-2 border-dashed border-brand-black bg-brand-cream px-3 py-8 text-sm font-medium text-brand-black"
            />
          </label>

          <label className="flex gap-3 border-2 border-brand-black bg-brand-mint p-3">
            <input type="checkbox" className="mt-1 h-4 w-4 accent-brand-pink" />
            <span className="text-sm font-medium leading-6 text-brand-black">
              I understand this demo analyzes visible signals in my photo and deletes
              temporary data after the session finishes or expires.
            </span>
          </label>

          <button
            type="button"
            className="border-2 border-brand-black bg-brand-orange px-4 py-3 text-sm font-black text-brand-black transition hover:-translate-y-0.5 hover:shadow-[4px_4px_0_#000]"
          >
            Submit photo
          </button>
        </form>
      </div>
    </main>
  );
}
