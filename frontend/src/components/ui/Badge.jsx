import { cn } from "@/lib/utils";
const badgeVariants = {
    exact: "ui-badge--green",
    similar: "ui-badge--amber",
    new: "ui-badge--blue",
    pending: "ui-badge--amber",
    reviewed: "ui-badge--primary",
    duplicate: "ui-badge--red",
    clear: "ui-badge--green",
    active: "ui-badge--green",
    closed: "ui-badge--slate",
    upcoming: "ui-badge--blue",
    question: "ui-badge--primary",
    motion: "ui-badge--accent",
    admin: "ui-badge--primary",
    seniorClerk: "ui-badge--amber",
    clerk: "ui-badge--slate",
    inactive: "ui-badge--red",
    info: "ui-badge--blue",
};
export function Badge({ children, variant = "info", className }) {
    return (<span className={cn("ui-badge", badgeVariants[variant], className)}>
      {children}
    </span>);
}
