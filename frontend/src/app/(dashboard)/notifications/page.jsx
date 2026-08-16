"use client";

import { Bell, CheckCircle2, FileText, ShieldCheck, UserRound } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader } from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { formatDateTime } from "@/lib/utils";

function humanizeAction(action = "system_update") {
    return action
        .replaceAll("_", " ")
        .replace(/\b\w/g, (character) => character.toUpperCase());
}

function notificationIcon(action = "", entityType = "") {
    if (action.includes("login") || action.includes("logout") || entityType === "auth") return ShieldCheck;
    if (action.includes("user") || entityType === "user") return UserRound;
    if (action.includes("approve") || action.includes("review")) return CheckCircle2;
    if (entityType.includes("submission") || entityType.includes("record")) return FileText;
    return Bell;
}

export default function NotificationsPage() {
    const [notifications, setNotifications] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetch("/api/notifications?limit=50")
            .then(async (response) => {
                const data = await response.json().catch(() => []);
                if (!response.ok) throw new Error(data.message || "Could not load notifications");
                setNotifications(Array.isArray(data) ? data : []);
                setError(null);
            })
            .catch((requestError) => {
                setNotifications([]);
                setError(requestError.message || "Could not load notifications");
            })
            .finally(() => setIsLoading(false));
    }, []);

    return (
        <div className="notifications-page">
            <PageHeader
                title="Notifications"
                description="System activity, submission updates and account events relevant to you."
                showBreadcrumbs={false}
            />

            {isLoading ? (
                <div className="page-loading">
                    <Spinner className="page-loading__spinner" />
                    <p className="page-loading__text">Loading notifications...</p>
                </div>
            ) : error ? (
                <EmptyState title="Notifications unavailable" description={error} />
            ) : notifications.length === 0 ? (
                <EmptyState title="No notifications" description="New system activity will appear here." />
            ) : (
                <section className="notifications-page__list" aria-label="System notifications">
                    {notifications.map((notification) => {
                        const Icon = notificationIcon(notification.action, notification.entity_type || "");
                        return (
                            <article className="notifications-page__item" key={notification.id}>
                                <span className="notifications-page__icon-wrap" aria-hidden="true">
                                    <Icon className="notifications-page__icon" />
                                </span>
                                <div className="notifications-page__content">
                                    <div className="notifications-page__heading">
                                        <h2>{humanizeAction(notification.action)}</h2>
                                        <time dateTime={notification.created_at}>{formatDateTime(notification.created_at)}</time>
                                    </div>
                                    <p>{notification.details || "A system activity was recorded."}</p>
                                    <span className="notifications-page__actor">
                                        {notification.user_name || "System"}
                                    </span>
                                </div>
                            </article>
                        );
                    })}
                </section>
            )}
        </div>
    );
}
