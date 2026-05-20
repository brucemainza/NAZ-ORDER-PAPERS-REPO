import { jwtVerify } from "jose";

export const AUTH_COOKIE_NAME = "naz_token";

function getJwtSecretKey() {
    const secret = process.env.JWT_SECRET ?? "naz-order-papers-jwt-secret-change-in-production";
    return new TextEncoder().encode(secret);
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