import { NextResponse } from "next/server";
import { AUTH_COOKIE_NAME, verifyAuthToken } from "@/lib/auth";
const protectedPaths = ["/dashboard", "/submit", "/search", "/results", "/sessions", "/users", "/audit", "/reports"];
export async function middleware(request) {
    var _a;
    const token = (_a = request.cookies.get(AUTH_COOKIE_NAME)) === null || _a === void 0 ? void 0 : _a.value;
    const pathname = request.nextUrl.pathname;
    const isProtected = protectedPaths.some((path) => pathname.startsWith(path));
    if (!isProtected) {
        if (pathname === "/login" && token) {
            const payload = await verifyAuthToken(token);
            if (payload) {
                return NextResponse.redirect(new URL("/dashboard", request.url));
            }
        }
        return NextResponse.next();
    }
    if (!token) {
        return NextResponse.redirect(new URL("/login", request.url));
    }
    const payload = await verifyAuthToken(token);
    if (!payload) {
        const response = NextResponse.redirect(new URL("/login", request.url));
        response.cookies.set(AUTH_COOKIE_NAME, "", { maxAge: 0, path: "/" });
        return response;
    }
    return NextResponse.next();
}
export const config = {
    matcher: ["/dashboard/:path*", "/submit/:path*", "/search/:path*", "/results/:path*", "/sessions/:path*", "/users/:path*", "/audit/:path*", "/reports/:path*", "/login"],
};
