import { forwardRef } from "react";
import { cn } from "@/lib/utils";
export function buttonStyles({ variant = "primary", size = "md", fullWidth = false, className, }) {
    return cn("ui-button", {
        "ui-button--full-width": fullWidth,
        "ui-button--primary": variant === "primary",
        "ui-button--secondary": variant === "secondary",
        "ui-button--danger": variant === "danger",
        "ui-button--ghost": variant === "ghost",
        "ui-button--sm": size === "sm",
        "ui-button--md": size === "md",
        "ui-button--lg": size === "lg",
    }, className);
}
export const Button = forwardRef(function Button({ className, variant = "primary", size = "md", fullWidth = false, type = "button", ...props }, ref) {
    return <button ref={ref} type={type} className={buttonStyles({ variant, size, fullWidth, className })} {...props}/>;
});
