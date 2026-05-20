import { forwardRef } from "react";
import { cn } from "@/lib/utils";
export function buttonStyles({ variant = "primary", size = "md", fullWidth = false, className, }) {
    return cn("inline-flex items-center justify-center gap-2 rounded-md border text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-[--primary] focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60", {
        "w-full": fullWidth,
        "border-transparent bg-[--primary] px-4 py-2 text-white hover:bg-[--primary-dark]": variant === "primary",
        "border-[--border] bg-white px-4 py-2 text-[--black] hover:bg-[--bg]": variant === "secondary",
        "border-transparent bg-[--danger] px-4 py-2 text-white hover:bg-red-800": variant === "danger",
        "border-transparent bg-transparent px-3 py-2 text-[--primary] hover:bg-[--primary-light]": variant === "ghost",
        "px-3 py-1.5 text-xs": size === "sm",
        "px-4 py-2 text-sm": size === "md",
        "px-4 py-2.5 text-sm": size === "lg",
    }, className);
}
export const Button = forwardRef(function Button({ className, variant = "primary", size = "md", fullWidth = false, type = "button", ...props }, ref) {
    return <button ref={ref} type={type} className={buttonStyles({ variant, size, fullWidth, className })} {...props}/>;
});
