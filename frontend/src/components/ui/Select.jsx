import { ChevronDown } from "lucide-react";
import { forwardRef } from "react";
import { cn } from "@/lib/utils";
export const Select = forwardRef(function Select({ className, label, error, hint, children, id, ...props }, ref) {
    return (<label className="block space-y-1.5" htmlFor={id}>
      {label ? <span className="block text-sm font-medium text-[--black]">{label}</span> : null}
      <span className="relative block">
        <select ref={ref} id={id} className={cn("w-full appearance-none rounded-md border border-[--border] bg-white px-3 py-2 pr-10 text-sm text-[--black] outline-none transition-colors focus:border-[--primary] focus:ring-2 focus:ring-[--primary-light]", error && "border-[--danger] focus:border-[--danger] focus:ring-red-100", className)} {...props}>
          {children}
        </select>
        <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[--muted]"/>
      </span>
      {error ? <span className="text-xs text-[--danger]">{error}</span> : hint ? <span className="text-xs text-[--muted]">{hint}</span> : null}
    </label>);
});
