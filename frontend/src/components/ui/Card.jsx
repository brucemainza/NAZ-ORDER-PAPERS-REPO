import { cn } from "@/lib/utils";
export function Card({ children, className, }) {
    return <section className={cn("ui-card", className)}>{children}</section>;
}
