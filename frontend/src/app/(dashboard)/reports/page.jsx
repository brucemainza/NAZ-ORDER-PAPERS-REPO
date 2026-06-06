import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/layout/PageHeader";
const reportCards = [
    {
        title: "Submissions by Session",
        description: "Track drafting volume across parliamentary sessions and see where question and motion activity is concentrated.",
    },
    {
        title: "Match Rate Over Time",
        description: "Monitor how frequently new submissions resemble historical records and how review outcomes shift over time.",
    },
    {
        title: "Member Activity",
        description: "Review submission trends by Member of Parliament, subject area and originating ministry.",
    },
];
export default function ReportsPage() {
    return (<div>
      <PageHeader title="Reports" description="High-level operational reporting for parliamentary submissions, similarity outcomes and drafting activity."/>

      <div className="grid gap-5 xl:grid-cols-3">
        {reportCards.map((card) => (<Card key={card.title} className="p-5">
            <h2 className="text-base font-medium text-[--black]">{card.title}</h2>
            <p className="mt-2 text-sm text-[--muted]">{card.description}</p>
            <div className="mt-5 rounded-md border border-dashed border-[--border] bg-[--bg] px-4 py-16 text-center text-sm text-[--muted]">
              {/* TODO: Replace with production chart component once reporting endpoints are available. */}
              Chart coming soon
            </div>
          </Card>))}
      </div>
    </div>);
}
