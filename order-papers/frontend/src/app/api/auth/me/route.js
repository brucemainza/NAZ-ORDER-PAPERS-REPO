import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { AUTH_COOKIE_NAME, verifyAuthToken } from "@/lib/auth";
import db from "@/lib/db";

export const runtime = 'nodejs';

export async function GET() {
    const token = cookies().get(AUTH_COOKIE_NAME)?.value;
    if (!token) {
        return NextResponse.json({ message: "Unauthenticated" }, { status: 401 });
    }
    
    const payload = await verifyAuthToken(token);
    if (!payload) {
        return NextResponse.json({ message: "Invalid session" }, { status: 401 });
    }
    
    const sessionResult = await db.query(
        'SELECT revoked_at FROM user_sessions WHERE token_jti = $1',
        [payload.jti]
    );
    
    if (sessionResult.rows[0]?.revoked_at) {
        const response = NextResponse.json({ message: "Session revoked" }, { status: 401 });
        response.cookies.set(AUTH_COOKIE_NAME, "", { maxAge: 0, path: "/" });
        return response;
    }
    
    const userResult = await db.query(
        'SELECT id, employee_id, name, role, status, last_login_at FROM users WHERE id = $1',
        [payload.sub]
    );
    
    const user = userResult.rows[0];
    if (!user) {
        return NextResponse.json({ message: "User not found" }, { status: 404 });
    }
    
    if (user.status !== "Active") {
        const response = NextResponse.json({ message: "Account inactive" }, { status: 401 });
        response.cookies.set(AUTH_COOKIE_NAME, "", { maxAge: 0, path: "/" });
        return response;
    }
    
    return NextResponse.json({ 
        user: {
            id: user.id,
            name: user.name,
            employeeId: user.employee_id,
            role: user.role,
            status: user.status,
            lastLogin: user.last_login_at,
        }
    });
}