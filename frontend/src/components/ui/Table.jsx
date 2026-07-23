import { cn } from "@/lib/utils";
export function Table({ columns, data, rowKey, emptyMessage = "No data available." }) {
    return (<div className="ui-table-wrap">
      <table className="ui-table">
        <thead className="ui-table__head">
          <tr>
            {columns.map((column) => (<th key={column.key} className={cn("ui-table__heading", column.className)}>
                {column.header}
              </th>))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (<tr>
              <td className="ui-table__cell ui-table__cell--empty" colSpan={columns.length}>
                {emptyMessage}
              </td>
            </tr>) : (data.map((row) => (<tr key={rowKey(row)} className="ui-table__row">
                {columns.map((column) => (<td key={column.key} className={cn("ui-table__cell", column.className)}>
                    {column.render(row)}
                  </td>))}
              </tr>)))}
        </tbody>
      </table>
    </div>);
}
