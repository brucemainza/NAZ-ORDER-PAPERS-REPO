import { NextResponse } from "next/server";
import { authHeaders, BACKEND_URL } from "@/lib/backendProxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const MAX_MULTIPART_BYTES = 11 * 1024 * 1024;

export async function POST(request) {
    const contentType = request.headers.get("content-type") || "";
    if (!contentType.toLowerCase().startsWith("multipart/form-data;")) {
        return NextResponse.json(
            { message: "A multipart document upload is required" },
            { status: 415 }
        );
    }
    const declaredLength = Number(request.headers.get("content-length") || "0");
    if (Number.isFinite(declaredLength) && declaredLength > MAX_MULTIPART_BYTES) {
        return NextResponse.json(
            { message: "Upload is too large" },
            { status: 413 }
        );
    }

    const res = await fetch(`${BACKEND_URL}/submissions/upload`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": contentType }),
        body: request.body,
        duplex: "half",
    }).catch(() => null);

    if (!res) {
        return NextResponse.json({ message: "Backend service unavailable" }, { status: 502 });
    }

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        const message = typeof data.detail === "string" ? data.detail : "Upload failed";
        return NextResponse.json({ message }, { status: res.status });
    }

    return NextResponse.json(data, { status: res.status });
}
