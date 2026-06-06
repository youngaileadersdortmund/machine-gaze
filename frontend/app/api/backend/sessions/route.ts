import { adminHeaders, proxyJson } from "@/lib/backend-proxy";

export async function POST() {
  return proxyJson("/api/sessions", {
    method: "POST",
    headers: adminHeaders(),
  });
}
