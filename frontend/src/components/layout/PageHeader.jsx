"use client";
import { ChevronRight } from "lucide-react";
import { usePathname } from "next/navigation";
function prettifySegment(segment) {
    if (!segment) {
        return "Home";
    }
    if (segment === "search") {
        return "Submissions";
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
    return (<div className="page-header">
      <div>
        <div className="page-header__breadcrumbs">
          <span>Portal</span>
          {segments.map((segment) => (<span key={segment} className="page-header__breadcrumb">
              <ChevronRight className="page-header__breadcrumb-icon"/>
              <span>{prettifySegment(segment)}</span>
            </span>))}
        </div>
        <h1 className="page-header__title">{title}</h1>
        {description ? <p className="page-header__description">{description}</p> : null}
      </div>
      {actions ? <div className="page-header__actions">{actions}</div> : null}
    </div>);
}
