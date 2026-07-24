import { ChevronDown } from "lucide-react";
import { forwardRef } from "react";
import { cn } from "@/lib/utils";
export const Select = forwardRef(function Select({ className, label, error, hint, children, id, ...props }, ref) {
    return (<label className="ui-field" htmlFor={id}>
      {label ? <span className="ui-field__label">{label}</span> : null}
      <span className="ui-field__select-wrap">
        <select ref={ref} id={id} className={cn("ui-field__control ui-field__control--select", error && "ui-field__control--error", className)} {...props}>
          {children}
        </select>
        <ChevronDown className="ui-field__select-icon"/>
      </span>
      {error ? <span className="ui-field__message ui-field__message--error">{error}</span> : hint ? <span className="ui-field__message">{hint}</span> : null}
    </label>);
});
