import { CheckCheck, ClipboardCheck, Files, Landmark } from "lucide-react";
import Link from "next/link";
import { RecentActivity } from "@/components/dashboard/RecentActivity";
import { StatCard } from "@/components/dashboard/StatCard";
import { PageHeader } from "@/components/layout/PageHeader";
import { buttonStyles } from "@/components/ui/Button";
import { mockSessions, mockSubmissions } from "@/lib/mockData";
const dashboardStats = [
    { label: "Total Submissions", value: "246", description: "All logged submissions in the indexed archive.", icon: Files },
    { label: "Pending Review", value: "18", description: "Items waiting for clerk review and decision.", icon: ClipboardCheck },
    { label: "Exact Matches Found", value: "37", description: "Historical items flagged above the exact-match threshold.", icon: CheckCheck },
    { label: "Sessions Active", value: "1", description: "Current live parliamentary session open for drafting.", icon: Landmark },
];
export default function DashboardPage() {
    var _a;
    return (<div>
      <PageHeader title="Dashboard" description="Monitor activity across submissions, review queues and session coverage." actions={<Link href="/submit" className={buttonStyles({ variant: "primary" })}>
            New Submission
          </Link>}/>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {dashboardStats.map((stat) => (<StatCard key={stat.label} {...stat}/>))}
      </div>

      <section className="mt-6 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-medium text-[--black]">Recent Activity</h2>
            <p className="text-sm text-[--muted]">Latest submissions from the current and previous sessions.</p>
          </div>
          <span className="rounded-md border border-[--border] bg-white px-3 py-2 text-sm text-[--muted]">
            {(_a = mockSessions.find((session) => session.status === "Active")) === null || _a === void 0 ? void 0 : _a.name}
          </span>
        </div>
        <RecentActivity submissions={mockSubmissions.slice(0, 6)}/>
      </section>
    </div>);
}
