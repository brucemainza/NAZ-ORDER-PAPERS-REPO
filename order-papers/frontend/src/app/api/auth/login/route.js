import { NextResponse } from "next/server";
import { z } from "zod";
import { AUTH_COOKIE_NAME, getAuthCookieOptions, signAuthToken } from "@/lib/auth";
import db from "@/lib/db";
import bcrypt from "bcryptjs";

export const runtime = 'nodejs';

const loginSchema = z.object({
    employeeId: z.string().min(1, "Employee ID is required"),
    password: z.string().min(1, "Password is required"),
});

export async function POST(request) {
    const body = await request.json();
    const parsed = loginSchema.safeParse(body);
    if (!parsed.success) {
        return NextResponse.json({
            message: "Invalid credentials payload.",
        }, { status: 400 });
    }

    const { employeeId, password } = parsed.data;
    
    const result = await db.query(
        'SELECT id, employee_id, name, role, status, password_hash FROM users WHERE employee_id = $1',
        [employeeId.trim().toUpperCase()]
    );
    
    const user = result.rows[0];
    
    if (!user || user.status !== "Active") {
        return NextResponse.json({
            message: "Invalid employee ID or password.",
        }, { status: 401 });
    }
    
    if (!user.password_hash) {
        return NextResponse.json({
            message: "Invalid employee ID or password.",
        }, { status: 401 });
    }
    
    const validPassword = await bcrypt.compare(password, user.password_hash);
    if (!validPassword) {
        return NextResponse.json({
            message: "Invalid employee ID or password.",
        }, { status: 401 });
    }
    
    await db.query(
        'UPDATE users SET last_login_at = NOW() WHERE id = $1',
        [user.id]
    );
    
    const { token, jti } = await signAuthToken({
        id: user.id,
        employeeId: user.employee_id,
        name: user.name,
        role: user.role,
        status: user.status,
    });
    
    const ipAddress = request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ?? 
                      request.headers.get('x-real-ip') ?? 
                      null;
    const userAgent = request.headers.get('user-agent') ?? null;
    
    await db.query(
        `INSERT INTO user_sessions (user_id, token_jti, ip_address, user_agent, expires_at) 
         VALUES ($1, $2, $3, $4, NOW() + INTERVAL '8 hours')`,
        [user.id, jti, ipAddress, userAgent]
    );
    
    const response = NextResponse.json({ 
        token, 
        user: {
            id: user.id,
            name: user.name,
            employeeId: user.employee_id,
            role: user.role,
            status: user.status,
            lastLogin: new Date().toISOString(),
        }
    });
    response.cookies.set(AUTH_COOKIE_NAME, token, getAuthCookieOptions());
    return response;
}