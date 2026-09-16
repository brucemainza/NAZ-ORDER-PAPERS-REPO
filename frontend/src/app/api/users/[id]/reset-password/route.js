import { proxyJson } from "@/lib/backendProxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(_request, { params }) {
    return proxyJson(`/users/${params.id}/reset-password`, {
        method: "POST",
    });
}
