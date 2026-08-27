"use client";
import { CheckCheck, ClipboardCheck, Files, Landmark } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { RecentActivity } from "@/components/dashboard/RecentActivity";
import { StatCard } from "@/components/dashboard/StatCard";
import { PageHeader } from "@/components/layout/PageHeader";
import { buttonStyles } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { normalizeSubmission } from "@/lib/records";

export default function DashboardPage() {
    const [reports, setReports] = useState(null);
    const [records, setRecords] = useState([]);
    const [sessions, setSessions] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        Promise.all([
            fetch("/api/reports").then((response) => response.json().then((data) => ({ ok: response.ok, data }))),
            fetch("/api/records").then((response) => response.json().then((data) => ({ ok: response.ok, data }))),
            fetch("/api/sessions").then((response) => response.json().then((data) => ({ ok: response.ok, data }))),
        ])
            .then(([reportResult, recordResult, sessionResult]) => {
                if (!reportResult.ok) throw new Error(reportResult.data.message || "Failed to load dashboard data");
                setReports(reportResult.data);
                setRecords(Array.isArray(recordResult.data) ? recordResult.data.map(normalizeSubmission) : []);
                setSessions(Array.isArray(sessionResult.data) ? sessionResult.data : []);
                setError(null);
            })
            .catch((err) => setError(err.message || "Failed to load dashboard data"))
            .finally(() => setIsLoading(false));
    }, []);

    const stats = useMemo(() => {
        const sessionReports = reports?.submissions_by_session || [];
        const totalSubmissions = sessionReports.reduce((sum, item) => sum + item.total, 0);
        const pendingReview = sessionReports.reduce((sum, item) => sum + item.pending_review, 0);
        const duplicateMatches = sessionReports.reduce((sum, item) => sum + item.duplicates, 0);
        const activeSessions = sessions.filter((session) => session.status === "Active").length;
        return [
            { label: "Total Submissions", value: String(totalSubmissions), description: "All logged submissions in the indexed archive.", icon: Files },
            { label: "Under Review", value: String(pendingReview), description: "Items waiting for clerk review and decision.", icon: ClipboardCheck },
            { label: "Duplicate Matches", value: String(duplicateMatches), description: "Items reviewers marked as duplicate historical matters.", icon: CheckCheck },
            { label: "Sessions Active", value: String(activeSessions), description: "Current parliamentary sessions open for drafting.", icon: Landmark },
        ];
    }, [reports, sessions]);

    const activeSession = sessions.find((session) => session.status === "Active");

    return (<div>
      <PageHeader title="Dashboard" actions={<Link href="/submit" className={buttonStyles({ variant: "primary" })}>
            New Submission
          </Link>}/>

      {isLoading ? (<div className="dashboard-page__loading">
          <Spinner className="dashboard-page__spinner"/>
          <p className="dashboard-page__loading-text">Loading dashboard data...</p>
        </div>) : error ? (<EmptyState title="Dashboard unavailable" description={error}/>) : (<>
        <div className="dashboard-page__stats">
          {stats.map((stat) => (<StatCard key={stat.label} {...stat}/>))}
        </div>

        <section className="dashboard-page__activity">
          <div className="dashboard-page__activity-header">
            <div>
              <h2 className="dashboard-page__activity-title">Recent Activity</h2>
              <p className="dashboard-page__activity-description">Latest records from the current and previous sessions.</p>
            </div>
            {activeSession ? (<span className="dashboard-page__session">
              {activeSession.name}
            </span>) : null}
          </div>
          <RecentActivity submissions={records.slice(0, 4)} sessions={sessions}/>
        </section>
      </>)}
    </div>);
}
