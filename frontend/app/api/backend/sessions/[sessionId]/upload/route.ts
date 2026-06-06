import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { backendUrl } from "@/lib/backend-proxy";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> },
) {
  const { sessionId } = await params;
  const token = request.nextUrl.searchParams.get("token") || "";
  const formData = await request.formData();
  const upstreamUrl = new URL(backendUrl(`/api/sessions/${encodeURIComponent(sessionId)}/upload`));
  upstreamUrl.searchParams.set("token", token);

  try {
    const response = await fetch(upstreamUrl, {
      method: "POST",
      body: formData,
      cache: "no-store",
    });
    const body = await response.text();
    return new Response(body, {
      status: response.status,
      headers: {
        "content-type": response.headers.get("content-type") || "application/json",
      },
    });
  } catch (error) {
    return NextResponse.json(
      { detail: error instanceof Error ? error.message : "Backend upload request failed." },
      { status: 502 },
    );
  }
}
