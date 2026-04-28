import { cn } from "@/lib/utils";
export function Table({ columns, data, rowKey, emptyMessage = "No data available." }) {
    return (<div className="overflow-x-auto rounded-md border border-[--border] bg-[--surface] shadow-sm">
      <table className="table-stripes min-w-full text-left text-sm">
        <thead className="bg-[--sidebar] text-white">
          <tr>
            {columns.map((column) => (<th key={column.key} className={cn("px-4 py-3 text-xs font-semibold uppercase tracking-wide", column.className)}>
                {column.header}
              </th>))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (<tr>
              <td className="px-4 py-6 text-sm text-[--muted]" colSpan={columns.length}>
                {emptyMessage}
              </td>
            </tr>) : (data.map((row) => (<tr key={rowKey(row)} className="border-t border-[--border] align-top">
                {columns.map((column) => (<td key={column.key} className={cn("px-4 py-3 text-sm text-[--black]", column.className)}>
                    {column.render(row)}
                  </td>))}
              </tr>)))}
        </tbody>
      </table>
    </div>);
}
