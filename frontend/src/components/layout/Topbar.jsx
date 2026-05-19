"use client";
import { ShieldCheck } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
export function Topbar() {
    var _a;
    const { user } = useAuth();
    return (<header className="flex min-h-16 items-center justify-between border-b border-[--border] bg-white px-6">
      <div>
        <p className="text-xs uppercase tracking-wide text-[--muted]">National Assembly of Zambia</p>
        <p className="text-sm font-medium text-[--black]">Order Papers System</p>
      </div>
      <div className="flex items-center gap-3 rounded-md border border-[--border] bg-[--bg] px-3 py-2 text-sm">
        <ShieldCheck className="h-4 w-4 text-[--primary]"/>
        <div className="text-right">
          <p className="font-medium text-[--black]">{(_a = user === null || user === void 0 ? void 0 : user.role) !== null && _a !== void 0 ? _a : "Secure Session"}</p>
          <p className="text-xs text-[--muted]">{new Intl.DateTimeFormat("en-ZM", { dateStyle: "medium" }).format(new Date())}</p>
        </div>
      </div>
    </header>);
}
