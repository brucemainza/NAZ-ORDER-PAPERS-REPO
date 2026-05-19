import { cn } from "@/lib/utils";
const badgeVariants = {
    exact: "border-green-200 bg-green-50 text-green-800",
    similar: "border-amber-200 bg-amber-50 text-amber-800",
    new: "border-blue-200 bg-blue-50 text-blue-800",
    pending: "border-amber-200 bg-amber-50 text-amber-800",
    reviewed: "border-[--primary-light] bg-[--primary-light] text-[--primary-dark]",
    duplicate: "border-red-200 bg-red-50 text-red-800",
    clear: "border-green-200 bg-green-50 text-green-800",
    active: "border-green-200 bg-green-50 text-green-800",
    closed: "border-slate-200 bg-slate-100 text-slate-700",
    upcoming: "border-blue-200 bg-blue-50 text-blue-800",
    question: "border-[--primary-light] bg-[--primary-light] text-[--primary-dark]",
    motion: "border-[--accent-light] bg-[--accent-light] text-[--accent]",
    admin: "border-[--primary-light] bg-[--primary-light] text-[--primary-dark]",
    seniorClerk: "border-amber-200 bg-amber-50 text-amber-800",
    clerk: "border-slate-200 bg-slate-100 text-slate-700",
    inactive: "border-red-200 bg-red-50 text-red-800",
    info: "border-blue-200 bg-blue-50 text-blue-800",
};
export function Badge({ children, variant = "info", className }) {
    return (<span className={cn("inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium", badgeVariants[variant], className)}>
      {children}
    </span>);
}
