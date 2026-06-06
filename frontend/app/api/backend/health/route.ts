import { proxyJson } from "@/lib/backend-proxy";

export async function GET() {
  return proxyJson("/health");
}
