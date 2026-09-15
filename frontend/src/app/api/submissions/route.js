import { NextResponse } from "next/server";
import { authHeaders, backendErrorMessage, BACKEND_URL } from "@/lib/backendProxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request) {
    const body = await request.json();
    const res = await fetch(`${BACKEND_URL}/submissions`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(body),
    }).catch(() => null);

    if (!res) {
        return NextResponse.json({ message: "Backend service unavailable" }, { status: 502 });
    }

    const data = await res.json().catch(() => ({}));

    if (res.status === 409 && data?.detail?.code === "possible_duplicate") {
        return NextResponse.json({ duplicate: data.detail }, { status: 409 });
    }

    if (!res.ok) {
        return NextResponse.json({ message: backendErrorMessage(data) }, { status: res.status });
    }

    return NextResponse.json(data, { status: res.status });
}
