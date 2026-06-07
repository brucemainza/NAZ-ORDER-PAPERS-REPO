import { proxyJson } from "@/lib/backendProxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(_request, { params }) {
    return proxyJson(`/records/${params.id}/reviews`);
}

export async function POST(request, { params }) {
    const body = await request.json();
    return proxyJson(`/records/${params.id}/reviews`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}
