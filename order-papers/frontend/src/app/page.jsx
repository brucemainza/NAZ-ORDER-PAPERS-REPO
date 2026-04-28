import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { AUTH_COOKIE_NAME, verifyAuthToken } from "@/lib/auth";
export default async function HomePage() {
    var _a;
    const token = (_a = cookies().get(AUTH_COOKIE_NAME)) === null || _a === void 0 ? void 0 : _a.value;
    if (token) {
        const payload = await verifyAuthToken(token);
        if (payload) {
            redirect("/dashboard");
        }
    }
    redirect("/login");
}
