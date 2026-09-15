import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { AUTH_COOKIE_NAME } from "@/lib/auth";

export const BACKEND_URL = process.env.BACKEND_INTERNAL_URL || "http://backend:8000";

export function authHeaders(extra = {}) {
    const token = cookies().get(AUTH_COOKIE_NAME)?.value;
    return {
        ...extra,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
}

export function backendErrorMessage(data) {
    if (Array.isArray(data.detail)) {
        return data.detail
            .map((error) => {
                const field = Array.isArray(error.loc)
                    ? error.loc.filter((part) => part !== "body").join(".")
                    : "";
                return [field, error.msg].filter(Boolean).join(": ");
            })
            .join("; ");
    }
    if (typeof data.detail === "string") {
        return data.detail;
    }
    if (typeof data.message === "string") {
        return data.message;
    }
    return "Backend request failed";
}

export async function proxyJson(url, options = {}) {
    const res = await fetch(`${BACKEND_URL}${url}`, {
        ...options,
        headers: authHeaders(options.headers),
    }).catch(() => null);

    if (!res) {
        return NextResponse.json({ message: "Backend service unavailable" }, { status: 502 });
    }

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        return NextResponse.json(
            { message: backendErrorMessage(data) },
            { status: res.status }
        );
    }

    return NextResponse.json(data, { status: res.status });
}
