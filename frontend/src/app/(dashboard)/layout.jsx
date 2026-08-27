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

    return (<div className="dashboard-shell">
      <Sidebar />
      <div className="dashboard-shell__content">
        <Topbar />
        <main className="dashboard-shell__main">{children}</main>
      </div>
    </div>);
}
