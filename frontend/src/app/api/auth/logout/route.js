import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { AUTH_COOKIE_NAME } from "@/lib/auth";

const BACKEND_URL = process.env.BACKEND_INTERNAL_URL || "http://backend:8000";

export const runtime = 'nodejs';
export const dynamic = "force-dynamic";

export async function POST() {
    const token = cookies().get(AUTH_COOKIE_NAME)?.value;

    if (token) {
        await fetch(`${BACKEND_URL}/auth/logout`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${token}`,
            },
        }).catch(() => {});
    }

    const response = NextResponse.json({ success: true });
    response.cookies.set(AUTH_COOKIE_NAME, "", {
        httpOnly: true,
        sameSite: "lax",
        secure: process.env.NODE_ENV === "production",
        path: "/",
        maxAge: 0,
    });
    return response;
}
