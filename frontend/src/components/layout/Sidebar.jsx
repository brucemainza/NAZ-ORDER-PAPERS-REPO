"use client";
import { BarChart2, Calendar, ClipboardList, FilePlus, File, LayoutDashboard, LogOut, Users, } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils";
const navItems = [
    { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, adminOnly: false },
    { href: "/submit", label: "Submit", icon: FilePlus, adminOnly: false },
    { href: "/search", label: "Submissions", icon: File, adminOnly: false },
    { href: "/sessions", label: "Sessions", icon: Calendar, adminOnly: true },
    { href: "/users", label: "Users", icon: Users, adminOnly: true },
    { href: "/audit", label: "Audit Log", icon: ClipboardList, adminOnly: true },
    { href: "/reports", label: "Reports", icon: BarChart2, adminOnly: false },
];
export function Sidebar() {
    var _a, _b;
    const pathname = usePathname();
    const router = useRouter();
    const { user, logout } = useAuth();
    const isAdmin = (user === null || user === void 0 ? void 0 : user.role) === "Admin";
    const visibleItems = navItems.filter((item) => (item.adminOnly ? isAdmin : true));
    return (<aside className="flex min-h-screen w-full max-w-[272px] flex-col border-r border-black/10 bg-[--sidebar] text-[--sidebar-text]">
      <div className="border-b border-white/10 px-5 py-5">
        <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-md border border-white/15 bg-[--primary] text-sm font-semibold text-white">
          NAZ
        </div>
        <h1 className="text-base font-medium text-white">Order Papers System</h1>
        <p className="mt-1 text-sm text-[--sidebar-text]">Internal parliamentary records portal</p>
      </div>

      <nav className="flex-1 px-3 py-4">
        <ul className="space-y-1.5">
          {visibleItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
            const Icon = item.icon;
            return (<li key={item.href}>
                <Link href={item.href} className={cn("flex items-center gap-3 rounded-md border-l-4 px-3 py-2 text-sm transition-colors", isActive
                    ? "border-[--primary] bg-[--primary-light] text-[--primary]"
                    : "border-transparent text-[--sidebar-text] hover:bg-white/5 hover:text-white")}>
                  <Icon className="h-4 w-4"/>
                  <span>{item.label}</span>
                </Link>
              </li>);
        })}
        </ul>
      </nav>

      <div className="border-t border-white/10 px-4 py-4">
        <div className="mb-3 rounded-md border border-white/10 bg-white/5 px-3 py-3">
          <p className="text-sm font-medium text-white">{(_a = user === null || user === void 0 ? void 0 : user.name) !== null && _a !== void 0 ? _a : "Authenticated User"}</p>
          <p className="mt-1 text-xs text-[--sidebar-text]">{(_b = user === null || user === void 0 ? void 0 : user.role) !== null && _b !== void 0 ? _b : "Role unavailable"}</p>
        </div>
        <Button variant="ghost" fullWidth className="justify-center border border-white/10 text-[--sidebar-text] hover:bg-white/10 hover:text-white" onClick={async () => {
            await logout();
            router.push("/login");
        }}>
          <LogOut className="h-4 w-4"/>
          Logout
        </Button>
      </div>
    </aside>);
}
