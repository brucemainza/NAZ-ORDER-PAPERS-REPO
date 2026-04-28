"use client";
import { ChevronRight } from "lucide-react";
import { usePathname } from "next/navigation";
function prettifySegment(segment) {
    if (!segment) {
        return "Home";
    }
    if (segment.startsWith("sub-") || segment.startsWith("match-")) {
        return "Result Record";
    }
    return segment
        .replace(/-/g, " ")
        .replace(/\b\w/g, (character) => character.toUpperCase());
}
export function PageHeader({ title, description, actions, }) {
    const pathname = usePathname();
    const segments = pathname.split("/").filter(Boolean);
    return (<div className="mb-6 flex flex-col gap-4 border-b border-[--border] pb-4 md:flex-row md:items-end md:justify-between">
      <div>
        <div className="mb-2 flex flex-wrap items-center gap-1 text-xs text-[--muted]">
          <span>Portal</span>
          {segments.map((segment) => (<span key={segment} className="flex items-center gap-1">
              <ChevronRight className="h-3 w-3"/>
              <span>{prettifySegment(segment)}</span>
            </span>))}
        </div>
        <h1 className="text-xl font-semibold text-[--black]">{title}</h1>
        {description ? <p className="mt-1 text-sm text-[--muted]">{description}</p> : null}
      </div>
      {actions ? <div className="flex items-center gap-3">{actions}</div> : null}
    </div>);
}
