import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { AUTH_COOKIE_NAME, verifyAuthToken } from "@/lib/auth";
import { mockUsers } from "@/lib/mockData";
export async function GET() {
    var _a;
    const token = (_a = cookies().get(AUTH_COOKIE_NAME)) === null || _a === void 0 ? void 0 : _a.value;
    if (!token) {
        return NextResponse.json({ message: "Unauthenticated" }, { status: 401 });
    }
    const payload = await verifyAuthToken(token);
    if (!payload) {
        return NextResponse.json({ message: "Invalid session" }, { status: 401 });
    }
    const user = mockUsers.find((entry) => entry.id === payload.sub);
    if (!user) {
        return NextResponse.json({ message: "User not found" }, { status: 404 });
    }
    return NextResponse.json({ user });
}
