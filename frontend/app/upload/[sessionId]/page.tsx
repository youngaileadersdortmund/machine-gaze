import { GazeMark } from "@/components/gaze-mark";
import { UploadForm } from "@/components/upload-form";

export default async function UploadPage({
  params,
  searchParams,
}: {
  params: Promise<{ sessionId: string }>;
  searchParams: Promise<{ token?: string }>;
}) {
  const { sessionId } = await params;
  const { token = "" } = await searchParams;

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
            Add one photo to this private booth session. The backend strips metadata and
            deletes temporary data after the session finishes or expires.
          </p>
          <p className="mt-4 bg-brand-yellow px-3 py-2 font-mono text-sm font-black text-brand-black">
            {sessionId}
          </p>
        </section>

        <UploadForm sessionId={sessionId} token={token} />
      </div>
    </main>
  );
}
