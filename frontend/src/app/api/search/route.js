import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_INTERNAL_URL || "http://backend:8000";

export const runtime = 'nodejs';
export const dynamic = "force-dynamic";

export async function POST(request) {
    const body = await request.json();

    const res = await fetch(`${BACKEND_URL}/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });

    if (!res.ok) {
        return NextResponse.json({ message: "Search failed" }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data);
}
