"use client";

import { useEffect, useState } from "react";

import { ApiError, getSession, uploadSessionPhoto } from "@/lib/backend-api";

function messageFromError(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Could not submit the photo.";
}

export function UploadForm({ sessionId, token }: { sessionId: string; token: string }) {
  const [displayName, setDisplayName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [consent, setConsent] = useState(false);
  const [status, setStatus] = useState<"ready" | "uploading" | "submitted" | "closed" | "error">(
    token ? "ready" : "error",
  );
  const [message, setMessage] = useState(token ? "" : "This upload link is missing its session token.");

  useEffect(() => {
    let isActive = true;

    async function checkSession() {
      try {
        const session = await getSession(sessionId);
        if (!isActive) {
          return;
        }
        if (["deleted", "expired", "error", "ready", "uploaded", "processing"].includes(session.status)) {
          setStatus("closed");
          setMessage(
            session.status === "expired"
              ? "This upload session has expired."
              : "This upload session is no longer accepting photos.",
          );
        }
      } catch (error) {
        if (isActive) {
          setStatus("error");
          setMessage(messageFromError(error));
        }
      }
    }

    const timeout = window.setTimeout(() => {
      void checkSession();
    }, 0);

    return () => {
      isActive = false;
      window.clearTimeout(timeout);
    };
  }, [sessionId]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");

    if (!token) {
      setStatus("error");
      setMessage("This upload link is missing its session token.");
      return;
    }

    if (!displayName.trim()) {
      setStatus("error");
      setMessage("Please enter a display name or nickname.");
      return;
    }

    if (!file) {
      setStatus("error");
      setMessage("Please choose a photo.");
      return;
    }

    if (!consent) {
      setStatus("error");
      setMessage("Please confirm the consent checkbox before uploading.");
      return;
    }

    const formData = new FormData();
    formData.set("display_name", displayName.trim());
    formData.set("consent", "true");
    formData.set("file", file);

    setStatus("uploading");
    try {
      await uploadSessionPhoto(sessionId, token, formData);
      setStatus("submitted");
      setMessage("Photo submitted. You can return to the booth display.");
    } catch (error) {
      setStatus("error");
      setMessage(messageFromError(error));
    }
  }

  const isClosed = status === "closed" || status === "submitted";
  const isUploading = status === "uploading";

  return (
    <form
      onSubmit={handleSubmit}
      className="grid gap-4 border-2 border-brand-black bg-white p-6 shadow-[8px_8px_0_#c5227b]"
    >
      <label className="grid gap-2">
        <span className="text-sm font-black uppercase tracking-[0.12em] text-brand-pink">
          Display name
        </span>
        <input
          type="text"
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
          placeholder="Use a nickname"
          disabled={isClosed || isUploading}
          className="border-2 border-brand-black bg-brand-cream px-3 py-3 text-base font-medium text-brand-black outline-none transition focus:shadow-[4px_4px_0_#eda913] disabled:cursor-not-allowed disabled:opacity-60"
        />
      </label>

      <label className="grid gap-2">
        <span className="text-sm font-black uppercase tracking-[0.12em] text-brand-pink">
          Photo
        </span>
        <input
          type="file"
          accept="image/png,image/jpeg,image/webp"
          onChange={(event) => setFile(event.target.files?.[0] || null)}
          disabled={isClosed || isUploading}
          className="border-2 border-dashed border-brand-black bg-brand-cream px-3 py-8 text-sm font-medium text-brand-black disabled:cursor-not-allowed disabled:opacity-60"
        />
      </label>

      <label className="flex gap-3 border-2 border-brand-black bg-brand-mint p-3">
        <input
          type="checkbox"
          checked={consent}
          onChange={(event) => setConsent(event.target.checked)}
          disabled={isClosed || isUploading}
          className="mt-1 h-4 w-4 accent-brand-pink disabled:cursor-not-allowed"
        />
        <span className="text-sm font-medium leading-6 text-brand-black">
          I understand this demo analyzes visible signals in my photo and deletes
          temporary data after the session finishes or expires.
        </span>
      </label>

      {message ? (
        <p
          className={[
            "border-2 border-brand-black px-3 py-2 text-sm font-bold leading-6",
            status === "submitted" ? "bg-brand-mint text-brand-black" : "bg-brand-yellow text-brand-black",
          ].join(" ")}
        >
          {message}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={isClosed || isUploading}
        className="border-2 border-brand-black bg-brand-orange px-4 py-3 text-sm font-black text-brand-black transition hover:-translate-y-0.5 hover:shadow-[4px_4px_0_#000] disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isUploading ? "Submitting..." : status === "submitted" ? "Submitted" : "Submit photo"}
      </button>
    </form>
  );
}
