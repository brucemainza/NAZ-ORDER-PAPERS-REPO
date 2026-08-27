import { SearchX } from "lucide-react";
export function EmptyState({ title, description, action, }) {
    return (<div className="ui-empty-state">
      <div className="ui-empty-state__icon-wrap">
        <SearchX className="ui-empty-state__icon"/>
      </div>
      <h3 className="ui-empty-state__title">{title}</h3>
      <p className="ui-empty-state__description">{description}</p>
      {action ? <div className="ui-empty-state__action">{action}</div> : null}
    </div>);
}
