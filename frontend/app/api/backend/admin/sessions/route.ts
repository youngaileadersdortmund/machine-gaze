import { adminHeaders, proxyJson } from "@/lib/backend-proxy";

export async function GET() {
  return proxyJson("/api/admin/sessions", {
    headers: adminHeaders(),
  });
}
