import { NextResponse } from "next/server";

import { adminHeaders, backendUrl } from "@/lib/backend-proxy";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ sessionId: string }> },
) {
  const { sessionId } = await params;

  try {
    const response = await fetch(
      backendUrl(`/api/sessions/${encodeURIComponent(sessionId)}/preview`),
      {
        cache: "no-store",
        headers: adminHeaders(),
      },
    );

    if (!response.ok) {
      const body = await response.text();
      return new Response(body, {
        status: response.status,
        headers: {
          "content-type": response.headers.get("content-type") || "application/json",
        },
      });
    }

    return new Response(response.body, {
      status: response.status,
      headers: {
        "cache-control": "no-store",
        "content-type": response.headers.get("content-type") || "application/octet-stream",
      },
    });
  } catch (error) {
    return NextResponse.json(
      { detail: error instanceof Error ? error.message : "Backend preview request failed." },
      { status: 502 },
    );
  }
}
