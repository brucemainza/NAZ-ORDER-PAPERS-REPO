"use client";

import {
    BarChart2,
    Calendar,
    ClipboardList,
    File,
    FilePlus,
    LayoutDashboard,
    Users,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { hasPermission } from "@/lib/auth";
import { cn } from "@/lib/utils";

const navItems = [
    { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { href: "/submit", label: "Submit", icon: FilePlus, permissions: ["submit_question", "submit_motion"] },
    { href: "/search", label: "Submissions", icon: File },
    { href: "/sessions", label: "Sessions", icon: Calendar, permissions: ["manage_sessions"] },
    { href: "/users", label: "Users", icon: Users, permissions: ["manage_users"] },
    { href: "/audit", label: "Audit Log", icon: ClipboardList, permissions: ["view_audit"] },
    { href: "/reports", label: "Reports", icon: BarChart2, permissions: ["view_reports"] },
];

export function Sidebar() {
    const pathname = usePathname();
    const { user } = useAuth();
    const visibleItems = navItems.filter(
        (item) => !item.permissions || item.permissions.some((permission) => hasPermission(user, permission)),
    );

    return (
        <aside className="sidebar">
            <div className="sidebar__brand">
                <p className="sidebar__eyebrow">Republic of Zambia</p>
                <h1 className="sidebar__title">National Assembly</h1>
            </div>

            <nav className="sidebar__nav" aria-label="Primary navigation">
                <ul className="sidebar__nav-list">
                    {visibleItems.map((item) => {
                        const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
                        const Icon = item.icon;
                        return (
                            <li key={item.href}>
                                <Link
                                    href={item.href}
                                    className={cn(
                                        "sidebar__nav-link",
                                        isActive ? "sidebar__nav-link--active" : "sidebar__nav-link--inactive",
                                    )}
                                >
                                    <Icon className="sidebar__icon" />
                                    <span>{item.label}</span>
                                </Link>
                            </li>
                        );
                    })}
                </ul>
            </nav>

            <div className="sidebar__footer">
                <p className="sidebar__footer-title">Order Papers Portal</p>
                <p className="sidebar__footer-version">v0.1.0 • Internal Use</p>
            </div>
        </aside>
    );
}
