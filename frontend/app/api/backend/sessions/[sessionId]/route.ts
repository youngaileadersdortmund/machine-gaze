import { proxyJson } from "@/lib/backend-proxy";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ sessionId: string }> },
) {
  const { sessionId } = await params;
  return proxyJson(`/api/sessions/${encodeURIComponent(sessionId)}`);
}
