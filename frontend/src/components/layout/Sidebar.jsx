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
    return (<aside className="sidebar">
      <div className="sidebar__brand">
        <div className="sidebar__mark">
          NAZ
        </div>
        <h1 className="sidebar__title">Order Papers System</h1>
        <p className="sidebar__description">Internal parliamentary records portal</p>
      </div>

      <nav className="sidebar__nav">
        <ul className="sidebar__nav-list">
          {visibleItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
            const Icon = item.icon;
            return (<li key={item.href}>
                <Link href={item.href} className={cn("sidebar__nav-link", isActive
                    ? "sidebar__nav-link--active"
                    : "sidebar__nav-link--inactive")}>
                  <Icon className="sidebar__icon"/>
                  <span>{item.label}</span>
                </Link>
              </li>);
        })}
        </ul>
      </nav>

      <div className="sidebar__footer">
        <div className="sidebar__user">
          <p className="sidebar__user-name">{(_a = user === null || user === void 0 ? void 0 : user.name) !== null && _a !== void 0 ? _a : "Authenticated User"}</p>
          <p className="sidebar__user-role">{(_b = user === null || user === void 0 ? void 0 : user.role) !== null && _b !== void 0 ? _b : "Role unavailable"}</p>
        </div>
        <Button variant="ghost" fullWidth className="sidebar__logout" onClick={async () => {
            await logout();
            router.push("/login");
        }}>
          <LogOut className="sidebar__icon"/>
          Logout
        </Button>
      </div>
    </aside>);
}
