import { proxyJson } from "@/lib/backendProxy";

export async function POST(request) {
    const body = await request.json();
    return proxyJson("/ai/explanations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}
