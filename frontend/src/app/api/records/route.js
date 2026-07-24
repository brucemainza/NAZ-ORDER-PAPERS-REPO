import { proxyJson } from "@/lib/backendProxy";

export const runtime = 'nodejs';
export const dynamic = "force-dynamic";

export async function GET(request) {
    const { searchParams } = new URL(request.url);
    const url = `/records${searchParams.toString() ? `?${searchParams.toString()}` : ""}`;
    return proxyJson(url);
}
