import { SignJWT, jwtVerify } from "jose";
import { randomUUID } from "crypto";

export const AUTH_COOKIE_NAME = "naz_token";

function getJwtSecretKey() {
    const secret = process.env.JWT_SECRET ?? "demo-order-papers-secret";
    return new TextEncoder().encode(secret);
}

export async function signAuthToken(user) {
    const jti = randomUUID();
    const token = await new SignJWT({
        employeeId: user.employeeId,
        name: user.name,
        role: user.role,
        status: user.status,
    })
        .setProtectedHeader({ alg: "HS256" })
        .setSubject(user.id)
        .setJti(jti)          // ← Fixed: was .setJWTID()
        .setIssuedAt()
        .setExpirationTime("8h")
        .sign(getJwtSecretKey());
    
    return { token, jti };
}

export async function verifyAuthToken(token) {
    try {
        const { payload } = await jwtVerify(token, getJwtSecretKey());
        return payload;
    } catch {
        return null;
    }
}

export function getAuthCookieOptions() {
    return {
        httpOnly: true,
        sameSite: "lax",
        secure: process.env.NODE_ENV === "production",
        path: "/",
        maxAge: 60 * 60 * 8,
    };
}

export function hasAdminAccess(role) {
    return role === "Admin";
}