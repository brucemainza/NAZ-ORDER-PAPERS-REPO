import { proxyJson } from "@/lib/backendProxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
    return proxyJson("/sessions");
}

export async function POST(request) {
    const body = await request.json();
    return proxyJson("/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}
