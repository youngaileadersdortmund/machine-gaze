import { NextResponse } from "next/server";

const JSON_HEADERS = {
  "content-type": "application/json",
};

export function backendUrl(path: string) {
  const baseUrl = process.env.BACKEND_INTERNAL_URL || "http://localhost:8000";
  return `${baseUrl.replace(/\/$/, "")}${path}`;
}

export function adminHeaders() {
  return {
    Authorization: `Bearer ${process.env.BACKEND_ADMIN_TOKEN || process.env.ADMIN_TOKEN || "dev-admin-token"}`,
  };
}

export async function proxyJson(path: string, init?: RequestInit) {
  try {
    const response = await fetch(backendUrl(path), {
      ...init,
      cache: "no-store",
      headers: {
        ...(init?.body ? JSON_HEADERS : {}),
        ...init?.headers,
      },
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
      { detail: error instanceof Error ? error.message : "Backend request failed." },
      { status: 502 },
    );
  }
}
