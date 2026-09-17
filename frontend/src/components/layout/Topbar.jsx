"use client";

import { Bell, ChevronDown, KeyRound, LogOut } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Toast } from "@/components/ui/Toast";
import { useAuth } from "@/hooks/useAuth";

const emptyPasswordForm = { currentPassword: "", newPassword: "", confirmPassword: "" };

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
    const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);
    const [passwordForm, setPasswordForm] = useState(emptyPasswordForm);
    const [passwordError, setPasswordError] = useState(null);
    const [passwordSuccess, setPasswordSuccess] = useState(false);
    const [isSavingPassword, setIsSavingPassword] = useState(false);

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

    const openPasswordModal = () => {
        setPasswordForm(emptyPasswordForm);
        setPasswordError(null);
        setPasswordSuccess(false);
        setIsPasswordModalOpen(true);
        setIsAccountMenuOpen(false);
    };

    const closePasswordModal = () => {
        setIsPasswordModalOpen(false);
        setPasswordForm(emptyPasswordForm);
        setPasswordError(null);
        setPasswordSuccess(false);
    };

    const submitPasswordChange = async () => {
        if (passwordForm.newPassword !== passwordForm.confirmPassword) {
            setPasswordError("New password and confirmation do not match.");
            return;
        }
        setIsSavingPassword(true);
        setPasswordError(null);
        try {
            const response = await fetch("/api/auth/change-password", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    current_password: passwordForm.currentPassword,
                    new_password: passwordForm.newPassword,
                }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(data.message || "Could not change password");
            setPasswordForm(emptyPasswordForm);
            setPasswordSuccess(true);
        } catch (changeError) {
            setPasswordError(changeError.message || "Could not change password");
        } finally {
            setIsSavingPassword(false);
        }
    };

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
                                onClick={openPasswordModal}
                            >
                                <KeyRound className="topbar__logout-icon" />
                                Change password
                            </button>
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

            <Modal
                isOpen={isPasswordModalOpen}
                onClose={closePasswordModal}
                title="Change Password"
                description="Update the password for your own account."
                footer={
                    <>
                        <Button variant="secondary" onClick={closePasswordModal}>
                            {passwordSuccess ? "Close" : "Cancel"}
                        </Button>
                        {!passwordSuccess ? (
                            <Button onClick={submitPasswordChange} disabled={isSavingPassword}>
                                {isSavingPassword ? "Saving..." : "Change Password"}
                            </Button>
                        ) : null}
                    </>
                }
            >
                {passwordError ? <Toast variant="error" title="Could not change password" description={passwordError} /> : null}
                {passwordSuccess ? (
                    <Toast variant="success" title="Password changed" description="Use your new password the next time you log in." />
                ) : (
                    <div className="topbar__password-form">
                        <Input
                            label="Current Password"
                            type="password"
                            value={passwordForm.currentPassword}
                            onChange={(event) => setPasswordForm((current) => ({ ...current, currentPassword: event.target.value }))}
                        />
                        <Input
                            label="New Password"
                            type="password"
                            hint="At least 8 characters."
                            value={passwordForm.newPassword}
                            onChange={(event) => setPasswordForm((current) => ({ ...current, newPassword: event.target.value }))}
                        />
                        <Input
                            label="Confirm New Password"
                            type="password"
                            value={passwordForm.confirmPassword}
                            onChange={(event) => setPasswordForm((current) => ({ ...current, confirmPassword: event.target.value }))}
                        />
                    </div>
                )}
            </Modal>
        </header>
    );
}
