import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { AUTH_COOKIE_NAME, verifyAuthToken } from "@/lib/auth";
import db from "@/lib/db";

export const runtime = 'nodejs';

export async function POST() {
    const token = cookies().get(AUTH_COOKIE_NAME)?.value;
    
    if (token) {
        const payload = await verifyAuthToken(token);
        if (payload?.jti) {
            await db.query(
                'UPDATE user_sessions SET revoked_at = NOW() WHERE token_jti = $1',
                [payload.jti]
            );
        }
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