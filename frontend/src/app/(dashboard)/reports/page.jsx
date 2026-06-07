"use client";
import { useEffect, useMemo, useState } from "react";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { Table } from "@/components/ui/Table";
import { PageHeader } from "@/components/layout/PageHeader";
import { formatDate } from "@/lib/utils";

export default function ReportsPage() {
    const [reports, setReports] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetch("/api/reports")
            .then(async (response) => {
                const data = await response.json().catch(() => ({}));
                if (!response.ok) throw new Error(data.message || "Failed to load reports");
                setReports(data);
                setError(null);
            })
            .catch((err) => setError(err.message || "Failed to load reports"))
            .finally(() => setIsLoading(false));
    }, []);

    const totals = useMemo(() => {
        const sessions = reports?.submissions_by_session || [];
        return {
            submissions: sessions.reduce((sum, item) => sum + item.total, 0),
            pending: sessions.reduce((sum, item) => sum + item.pending_review, 0),
            duplicates: sessions.reduce((sum, item) => sum + item.duplicates, 0),
        };
    }, [reports]);

    if (isLoading) {
        return (<div>
          <PageHeader title="Reports" description="High-level operational reporting for parliamentary submissions, similarity outcomes and drafting activity."/>
          <div className="rounded-md border border-[--border] bg-white px-6 py-10 text-center shadow-sm">
            <Spinner className="mx-auto h-6 w-6"/>
            <p className="mt-3 text-sm text-[--muted]">Loading report data...</p>
          </div>
        </div>);
    }

    if (error) {
        return (<div>
          <PageHeader title="Reports" description="High-level operational reporting for parliamentary submissions, similarity outcomes and drafting activity."/>
          <EmptyState title="Reports unavailable" description={error}/>
        </div>);
    }

    const sessionColumns = [
        { key: "session", header: "Session", render: (row) => row.session_name },
        { key: "total", header: "Total", render: (row) => row.total },
        { key: "questions", header: "Questions", render: (row) => row.questions },
        { key: "motions", header: "Motions", render: (row) => row.motions },
        { key: "pending", header: "Pending", render: (row) => row.pending_review },
        { key: "duplicates", header: "Duplicates", render: (row) => row.duplicates },
    ];
    const matchColumns = [
        { key: "period", header: "Date", render: (row) => formatDate(row.period) },
        { key: "reviews", header: "Reviews", render: (row) => row.total_reviews },
        { key: "matches", header: "Duplicate / Similar", render: (row) => row.duplicate_or_similar },
        { key: "rate", header: "Match Rate", render: (row) => `${row.match_rate}%` },
    ];
    const activityColumns = [
        { key: "name", header: "Name", render: (row) => row.name },
        { key: "dept", header: "Department", render: (row) => row.department || "n/a" },
        { key: "submissions", header: "Submissions", render: (row) => row.submissions },
        { key: "pending", header: "Pending", render: (row) => row.pending_review },
        { key: "duplicates", header: "Duplicates", render: (row) => row.duplicates },
    ];

    return (<div>
      <PageHeader title="Reports" description="High-level operational reporting for parliamentary submissions, similarity outcomes and drafting activity."/>

      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <Card className="p-5"><p className="text-sm text-[--muted]">Total submissions</p><p className="mt-2 text-3xl font-semibold text-[--black]">{totals.submissions}</p></Card>
        <Card className="p-5"><p className="text-sm text-[--muted]">Pending review</p><p className="mt-2 text-3xl font-semibold text-[--black]">{totals.pending}</p></Card>
        <Card className="p-5"><p className="text-sm text-[--muted]">Duplicates</p><p className="mt-2 text-3xl font-semibold text-[--black]">{totals.duplicates}</p></Card>
      </div>

      <div className="space-y-6">
        <section className="space-y-3">
          <h2 className="text-base font-medium text-[--black]">Submissions by Session</h2>
          <Table columns={sessionColumns} data={reports.submissions_by_session || []} rowKey={(row) => row.session_id}/>
        </section>
        <section className="space-y-3">
          <h2 className="text-base font-medium text-[--black]">Similarity Match Rate Over Time</h2>
          <Table columns={matchColumns} data={reports.similarity_match_rate || []} rowKey={(row) => row.period} emptyMessage="No review decisions have been recorded yet."/>
        </section>
        <section className="space-y-3">
          <h2 className="text-base font-medium text-[--black]">Member Activity</h2>
          <Table columns={activityColumns} data={reports.member_activity || []} rowKey={(row) => row.name}/>
        </section>
        <section className="space-y-3">
          <h2 className="text-base font-medium text-[--black]">Department Activity</h2>
          <Table columns={activityColumns} data={reports.department_activity || []} rowKey={(row) => row.name}/>
        </section>
      </div>
    </div>);
}
