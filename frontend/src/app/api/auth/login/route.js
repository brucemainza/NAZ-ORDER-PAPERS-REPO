import { NextResponse } from "next/server";
import { z } from "zod";
import { AUTH_COOKIE_NAME, getAuthCookieOptions } from "@/lib/auth";

const loginSchema = z.object({
    employeeId: z.string().min(1, "Employee ID is required"),
    password: z.string().min(1, "Password is required"),
});

const BACKEND_URL = process.env.BACKEND_INTERNAL_URL || "http://backend:8000";

export const runtime = 'nodejs';

export async function POST(request) {
    const body = await request.json();
    const parsed = loginSchema.safeParse(body);
    if (!parsed.success) {
        return NextResponse.json({ message: "Invalid credentials payload." }, { status: 400 });
    }

    const res = await fetch(`${BACKEND_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            employee_id: parsed.data.employeeId,
            password: parsed.data.password,
        }),
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Authentication failed" }));
        return NextResponse.json(
            { message: err.detail || "Authentication failed" },
            { status: res.status }
        );
    }

    const data = await res.json();
    const { token, user } = data;

    const response = NextResponse.json({ token, user });
    response.cookies.set(AUTH_COOKIE_NAME, token, getAuthCookieOptions());
    return response;
}