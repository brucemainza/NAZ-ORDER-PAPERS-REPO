import { proxyJson } from "@/lib/backendProxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function PATCH(request, { params }) {
    const body = await request.json();
    return proxyJson(`/sessions/${params.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}

export async function DELETE(_request, { params }) {
    return proxyJson(`/sessions/${params.id}`, {
        method: "DELETE",
    });
}
