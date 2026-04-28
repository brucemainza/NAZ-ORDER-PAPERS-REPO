import { AlertCircle, CheckCircle2, Info } from "lucide-react";
import { cn } from "@/lib/utils";
const toastConfig = {
    success: {
        icon: CheckCircle2,
        className: "border-green-200 bg-green-50 text-green-900",
    },
    error: {
        icon: AlertCircle,
        className: "border-red-200 bg-red-50 text-red-900",
    },
    info: {
        icon: Info,
        className: "border-blue-200 bg-blue-50 text-blue-900",
    },
};
export function Toast({ title, description, variant = "info", }) {
    const { icon: Icon, className } = toastConfig[variant];
    return (<div className={cn("rounded-md border px-3 py-3 text-sm shadow-sm", className)}>
      <div className="flex items-start gap-2">
        <Icon className="mt-0.5 h-4 w-4 shrink-0"/>
        <div>
          <p className="font-medium">{title}</p>
          {description ? <p className="mt-1 text-xs opacity-90">{description}</p> : null}
        </div>
      </div>
    </div>);
}
