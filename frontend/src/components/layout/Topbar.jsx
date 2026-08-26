"use client";

import { Bell, ChevronDown, LogOut } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/hooks/useAuth";

const PAGE_NAMES = {
    "/dashboard": "Dashboard",
    "/submit": "New Submission",
    "/search": "Submissions",
    "/sessions": "Parliamentary Sessions",
    "/users": "Users",
    "/audit": "Audit Trail",
    "/reports": "Reports",
    "/notifications": "Notifications",
};

function getPageName(pathname) {
    if (pathname.startsWith("/results/")) return "Submission Record";
    return PAGE_NAMES[pathname] ?? "Order Papers System";
}

export function Topbar() {
    const { user, logout } = useAuth();
    const pathname = usePathname();
    const router = useRouter();
    const accountRef = useRef(null);
    const [isAccountMenuOpen, setIsAccountMenuOpen] = useState(false);
    const [isLoggingOut, setIsLoggingOut] = useState(false);

    useEffect(() => {
        setIsAccountMenuOpen(false);
    }, [pathname]);

    useEffect(() => {
        const closeMenu = (event) => {
            if (accountRef.current && !accountRef.current.contains(event.target)) {
                setIsAccountMenuOpen(false);
            }
        };
        const closeOnEscape = (event) => {
            if (event.key === "Escape") setIsAccountMenuOpen(false);
        };
        document.addEventListener("pointerdown", closeMenu);
        document.addEventListener("keydown", closeOnEscape);
        return () => {
            document.removeEventListener("pointerdown", closeMenu);
            document.removeEventListener("keydown", closeOnEscape);
        };
    }, []);

    const handleLogout = async () => {
        setIsLoggingOut(true);
        try {
            await logout();
            router.replace("/login");
            router.refresh();
        } finally {
            setIsLoggingOut(false);
            setIsAccountMenuOpen(false);
        }
    };

    return (
        <header className="topbar">
            <div className="topbar__identity">
                <p className="topbar__page-name">{getPageName(pathname)}</p>
            </div>

            <div className="topbar__actions">
                <Link
                    href="/notifications"
                    className="topbar__notification"
                    aria-label="Open notifications"
                    title="Notifications"
                >
                    <Bell className="topbar__notification-icon" />
                </Link>

                <div className="topbar__account" ref={accountRef}>
                    <button
                        type="button"
                        className="topbar__account-trigger"
                        aria-label={`Account menu for ${user?.name ?? "authenticated user"}`}
                        aria-haspopup="menu"
                        aria-expanded={isAccountMenuOpen}
                        onClick={() => setIsAccountMenuOpen((current) => !current)}
                    >
                        <span className="topbar__name">{user?.name ?? "Authenticated User"}</span>
                        <span className="topbar__avatar" aria-hidden="true" />
                        <ChevronDown className="topbar__account-chevron" aria-hidden="true" />
                    </button>

                    {isAccountMenuOpen ? (
                        <div className="topbar__account-menu" role="menu">
                            <div className="topbar__account-summary">
                                <span className="topbar__account-label">Signed in as</span>
                                <strong>{user?.name ?? "Authenticated User"}</strong>
                            </div>
                            <button
                                type="button"
                                role="menuitem"
                                className="topbar__logout"
                                disabled={isLoggingOut}
                                onClick={handleLogout}
                            >
                                <LogOut className="topbar__logout-icon" />
                                {isLoggingOut ? "Logging out..." : "Log out"}
                            </button>
                        </div>
                    ) : null}
                </div>
            </div>
        </header>
    );
}
