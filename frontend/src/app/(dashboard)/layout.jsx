import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { AUTH_COOKIE_NAME } from "@/lib/auth";

const BACKEND_URL = process.env.BACKEND_INTERNAL_URL || "http://backend:8000";

export default async function DashboardLayout({ children }) {
    const token = cookies().get(AUTH_COOKIE_NAME)?.value;
    if (!token) {
        redirect("/login");
    }

    try {
        const res = await fetch(`${BACKEND_URL}/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
            cache: "no-store",
        });
        if (!res.ok) {
            redirect("/login");
        }
    }
    catch (err) {
        redirect("/login");
    }

    return (<div className="min-h-screen bg-[--bg] md:grid md:grid-cols-[272px_1fr]">
      <Sidebar />
      <div className="min-w-0">
        <Topbar />
        <main className="px-4 py-6 md:px-6">{children}</main>
      </div>
    </div>);
}
