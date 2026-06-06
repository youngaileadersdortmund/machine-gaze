import type { DemoSession } from "@/lib/booth-demo";
import { QRCodeSVG } from "qrcode.react";

const qrCells = [
  1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1, 0,
  1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1,
  1, 1, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1,
  0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0,
  1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1,
  0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0,
  1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1,
  1, 0, 1, 1, 1, 0, 0, 1, 0, 0, 1, 1,
  0, 1, 0, 0, 1, 1, 1, 0, 1, 1, 0, 0,
  1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1,
  1, 0, 0, 1, 0, 1, 0, 0, 1, 1, 0, 1,
  0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0,
];

export function QrCard({ session }: { session: DemoSession }) {
  return (
    <section className="border-2 border-brand-black bg-brand-mint p-5 shadow-[8px_8px_0_#000]">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-black uppercase tracking-[0.16em] text-brand-black">
            Current session
          </p>
          <p className="mt-1 font-mono text-sm font-bold text-brand-black">{session.id}</p>
        </div>
        <p className="rounded-full border-2 border-brand-black bg-brand-yellow px-3 py-1 text-xs font-black text-brand-black">
          expires in {session.expiresIn}
        </p>
      </div>

      <div className="mt-6 grid place-items-center border-2 border-brand-black bg-brand-cream p-5">
        <div className="grid h-56 w-56 place-items-center bg-white p-4 shadow-[5px_5px_0_#c5227b]">
          {session.uploadUrl ? (
            <QRCodeSVG
              value={session.uploadUrl}
              size={192}
              bgColor="#ffffff"
              fgColor="#000000"
              level="M"
              marginSize={1}
            />
          ) : (
            <div className="grid h-48 w-48 grid-cols-12 gap-1 bg-white">
              {qrCells.map((cell, index) => (
                <span key={`${cell}-${index}`} className={cell ? "bg-brand-black" : "bg-white"} />
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="mt-5 bg-brand-black px-4 py-3 text-white">
        <p className="text-xs font-black uppercase tracking-[0.18em] text-brand-mint">
          Upload link
        </p>
        <p className="mt-1 break-all font-mono text-sm text-white">{session.uploadUrl}</p>
      </div>
    </section>
  );
}
