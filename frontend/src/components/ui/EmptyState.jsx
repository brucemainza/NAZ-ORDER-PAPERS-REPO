import { SearchX } from "lucide-react";
export function EmptyState({ title, description, action, }) {
    return (<div className="rounded-md border border-dashed border-[--border] bg-white px-6 py-12 text-center shadow-sm">
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-md border border-[--border] bg-[--bg]">
        <SearchX className="h-5 w-5 text-[--muted]"/>
      </div>
      <h3 className="text-base font-medium text-[--black]">{title}</h3>
      <p className="mx-auto mt-2 max-w-xl text-sm text-[--muted]">{description}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>);
}
