import { proxyJson } from "@/lib/backendProxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request) {
    const { searchParams } = new URL(request.url);
    const query = searchParams.toString();
    return proxyJson(`/audit${query ? `?${query}` : ""}`);
}
