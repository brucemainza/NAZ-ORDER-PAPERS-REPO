import { AlertCircle, CheckCircle2, Info } from "lucide-react";
import { cn } from "@/lib/utils";
const toastConfig = {
    success: {
        icon: CheckCircle2,
        className: "ui-toast--success",
    },
    error: {
        icon: AlertCircle,
        className: "ui-toast--error",
    },
    info: {
        icon: Info,
        className: "ui-toast--info",
    },
};
export function Toast({ title, description, variant = "info", }) {
    const { icon: Icon, className } = toastConfig[variant];
    return (<div className={cn("ui-toast", className)}>
      <div className="ui-toast__content">
        <Icon className="ui-toast__icon"/>
        <div>
          <p className="ui-toast__title">{title}</p>
          {description ? <p className="ui-toast__description">{description}</p> : null}
        </div>
      </div>
    </div>);
}
