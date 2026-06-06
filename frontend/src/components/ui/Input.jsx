import { forwardRef } from "react";
import { cn } from "@/lib/utils";
export const Input = forwardRef(function Input({ className, label, error, hint, id, ...props }, ref) {
    return (<label className="block space-y-1.5" htmlFor={id}>
      {label ? <span className="block text-sm font-medium text-[--black]">{label}</span> : null}
      <input ref={ref} id={id} className={cn("w-full rounded-md border border-[--border] bg-white px-3 py-2 text-sm text-[--black] outline-none transition-colors placeholder:text-[--muted] focus:border-[--primary] focus:ring-2 focus:ring-[--primary-light]", error && "border-[--danger] focus:border-[--danger] focus:ring-red-100", className)} {...props}/>
      {error ? <span className="text-xs text-[--danger]">{error}</span> : hint ? <span className="text-xs text-[--muted]">{hint}</span> : null}
    </label>);
});
