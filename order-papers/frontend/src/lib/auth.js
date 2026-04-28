import { SignJWT, decodeJwt, jwtVerify } from "jose";
export const AUTH_COOKIE_NAME = "naz_token";
export const DEMO_PASSWORD = "Password123!";
function getJwtSecretKey() {
    var _a;
    const secret = (_a = process.env.JWT_SECRET) !== null && _a !== void 0 ? _a : "demo-order-papers-secret";
    return new TextEncoder().encode(secret);
}
export async function signAuthToken(user) {
    return new SignJWT({
        employeeId: user.employeeId,
        name: user.name,
        role: user.role,
        status: user.status,
    })
        .setProtectedHeader({ alg: "HS256" })
        .setSubject(user.id)
        .setIssuedAt()
        .setExpirationTime("8h")
        .sign(getJwtSecretKey());
}
export async function verifyAuthToken(token) {
    try {
        const { payload } = await jwtVerify(token, getJwtSecretKey());
        return payload;
    }
    catch {
        return null;
    }
}
export function decodeAuthToken(token) {
    try {
        return decodeJwt(token);
    }
    catch {
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
