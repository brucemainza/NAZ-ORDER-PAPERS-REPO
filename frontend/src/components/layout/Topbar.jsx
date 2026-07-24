"use client";
import { ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
export function Topbar() {
    var _a;
    const { user } = useAuth();
    const [currentDate, setCurrentDate] = useState("");

    useEffect(() => {
        setCurrentDate(new Intl.DateTimeFormat("en-ZM", {
            dateStyle: "medium",
        }).format(new Date()));
    }, []);

    return (<header className="topbar">
      <div>
        <p className="topbar__eyebrow">National Assembly of Zambia</p>
        <p className="topbar__title">Order Papers System</p>
      </div>
      <div className="topbar__session">
        <ShieldCheck className="topbar__icon"/>
        <div className="topbar__session-text">
          <p className="topbar__role">{(_a = user === null || user === void 0 ? void 0 : user.role) !== null && _a !== void 0 ? _a : "Secure Session"}</p>
          <p className="topbar__date">{currentDate}</p>
        </div>
      </div>
    </header>);
}
