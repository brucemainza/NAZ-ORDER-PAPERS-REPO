import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_INTERNAL_URL || "http://backend:8000";

export const runtime = 'nodejs';
export const dynamic = "force-dynamic";

export async function GET() {
    const res = await fetch(`${BACKEND_URL}/sessions`).catch(() => null);
    if (!res) {
        return NextResponse.json({ message: "Backend service unavailable" }, { status: 502 });
    }

    if (!res.ok) {
        return NextResponse.json({ message: "Failed to fetch sessions" }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data);
}
