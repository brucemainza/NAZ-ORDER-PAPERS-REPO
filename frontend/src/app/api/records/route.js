import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_INTERNAL_URL || "http://backend:8000";

export const runtime = 'nodejs';
export const dynamic = "force-dynamic";

export async function GET(request) {
    const { searchParams } = new URL(request.url);
    const sessionId = searchParams.get("session_id");
    const itemType = searchParams.get("item_type");

    let url = `${BACKEND_URL}/records`;
    const params = new URLSearchParams();
    if (sessionId) params.append("session_id", sessionId);
    if (itemType) params.append("item_type", itemType);
    if (params.toString()) url += `?${params.toString()}`;

    const res = await fetch(url).catch(() => null);
    if (!res) {
        return NextResponse.json({ message: "Backend service unavailable" }, { status: 502 });
    }

    if (!res.ok) {
        return NextResponse.json({ message: "Failed to fetch records" }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data);
}
