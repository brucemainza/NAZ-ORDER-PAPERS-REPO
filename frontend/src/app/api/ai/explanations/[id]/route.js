import { proxyJson } from "@/lib/backendProxy";

export async function GET(_request, { params }) {
    return proxyJson(`/ai/explanations/${params.id}`);
}
