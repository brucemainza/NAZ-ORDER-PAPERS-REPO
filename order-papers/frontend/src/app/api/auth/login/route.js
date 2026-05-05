import { NextResponse } from "next/server";
import { z } from "zod";
import { AUTH_COOKIE_NAME, DEMO_PASSWORD, getAuthCookieOptions, signAuthToken } from "@/lib/auth";
import { mockUsers } from "@/lib/mockData";
const loginSchema = z.object({
    employeeId: z.string().min(1, "Employee ID is required"),
    password: z.string().min(1, "Password is required"),
});
export async function POST(request) {
    const body = await request.json();
    const parsed = await loginSchema.safeParse(body);
    if (!parsed.success) {
        return NextResponse.json({
            message: "Invalid credentials payload.",
        }, { status: 400 });
    }
    const user = mockUsers.find((entry) => entry.employeeId.toLowerCase() === parsed.data.employeeId.trim().toLowerCase());
    // TODO: Replace mock user lookup with backend authentication request.
    if (!user || parsed.data.password !== DEMO_PASSWORD || user.status !== "Active") {
        return NextResponse.json({
            message: "Invalid employee ID or password.",
        }, { status: 401 });
    }
    const token = await signAuthToken(user);
    const response = NextResponse.json({ token, user });
    response.cookies.set(AUTH_COOKIE_NAME, token, getAuthCookieOptions());
    return response;
}
 