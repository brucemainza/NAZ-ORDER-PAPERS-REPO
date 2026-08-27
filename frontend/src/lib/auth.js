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
    const secureDefault = process.env.NODE_ENV === "production";
    const explicitSecure = process.env.SECURE_COOKIES;
    const secure = explicitSecure !== undefined ? explicitSecure === "true" : secureDefault;
    return {
        httpOnly: true,
        sameSite: "lax",
        secure,
        path: "/",
        maxAge: 60 * 60 * 8,
    };
}

export function hasPermission(user, permission) {
    return user?.permissions?.includes(permission) ?? false;
}
