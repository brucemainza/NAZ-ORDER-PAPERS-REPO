import { forwardRef } from "react";
import { cn } from "@/lib/utils";
export const Input = forwardRef(function Input({ className, label, error, hint, id, ...props }, ref) {
    return (<label className="ui-field" htmlFor={id}>
      {label ? <span className="ui-field__label">{label}</span> : null}
      <input ref={ref} id={id} className={cn("ui-field__control", error && "ui-field__control--error", className)} {...props}/>
      {error ? <span className="ui-field__message ui-field__message--error">{error}</span> : hint ? <span className="ui-field__message">{hint}</span> : null}
    </label>);
});
