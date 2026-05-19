import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { AUTH_COOKIE_NAME } from "@/lib/auth";

const BACKEND_URL = process.env.BACKEND_INTERNAL_URL || "http://backend:8000";

export const runtime = 'nodejs';

export async function GET() {
    const token = cookies().get(AUTH_COOKIE_NAME)?.value;
    if (!token) {
        return NextResponse.json({ message: "Unauthenticated" }, { status: 401 });
    }

    const res = await fetch(`${BACKEND_URL}/auth/me`, {
        headers: {
            "Authorization": `Bearer ${token}`,
        },
    });

    if (!res.ok) {
        const response = NextResponse.json(
            { message: "Invalid session" },
            { status: 401 }
        );
        response.cookies.set(AUTH_COOKIE_NAME, "", { maxAge: 0, path: "/" });
        return response;
    }

    const user = await res.json();
    return NextResponse.json({ user });
}