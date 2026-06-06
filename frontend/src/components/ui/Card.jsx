import { cn } from "@/lib/utils";
export function Card({ children, className, }) {
    return <section className={cn("rounded-md border border-[--border] bg-[--surface] shadow-sm", className)}>{children}</section>;
}
