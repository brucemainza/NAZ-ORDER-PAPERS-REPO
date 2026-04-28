import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
export function cn(...inputs) {
    return twMerge(clsx(inputs));
}
export function formatDate(date) {
    return new Intl.DateTimeFormat("en-ZM", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    }).format(new Date(date));
}
export function formatDateTime(date) {
    return new Intl.DateTimeFormat("en-ZM", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    }).format(new Date(date));
}
export function truncateText(value, limit = 180) {
    if (value.length <= limit) {
        return value;
    }
    return `${value.slice(0, limit).trimEnd()}...`;
}
