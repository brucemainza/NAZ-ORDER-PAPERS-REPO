import { Card } from "@/components/ui/Card";
export function StatCard({ label, value, description }) {
    return (<Card className="stat-card">
      <div className="stat-card__content">
        <div>
          <p className="stat-card__label">{label}</p>
          <p className="stat-card__value">{value}</p>
          <p className="stat-card__description">{description}</p>
        </div>
      </div>
    </Card>);
}
