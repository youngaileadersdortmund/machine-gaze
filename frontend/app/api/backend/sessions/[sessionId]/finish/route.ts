import { adminHeaders, proxyJson } from "@/lib/backend-proxy";

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ sessionId: string }> },
) {
  const { sessionId } = await params;
  return proxyJson(`/api/sessions/${encodeURIComponent(sessionId)}/finish`, {
    method: "POST",
    headers: adminHeaders(),
  });
}
