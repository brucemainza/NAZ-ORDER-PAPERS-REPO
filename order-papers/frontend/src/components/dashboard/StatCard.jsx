import { Card } from "@/components/ui/Card";
export function StatCard({ label, value, description, icon: Icon, }) {
    return (<Card className="p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm text-[--muted]">{label}</p>
          <p className="mt-2 text-2xl font-semibold text-[--black]">{value}</p>
          <p className="mt-2 text-xs text-[--muted]">{description}</p>
        </div>
        <div className="flex h-10 w-10 items-center justify-center rounded-md border border-[--border] bg-[--bg]">
          <Icon className="h-5 w-5 text-[--primary]"/>
        </div>
      </div>
    </Card>);
}
