"use client";
import { Download } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Spinner } from "@/components/ui/Spinner";
import { Table } from "@/components/ui/Table";
import { formatDateTime } from "@/lib/utils";

export default function AuditPage() {
    const [filters, setFilters] = useState({ user: "", action: "" });
    const [logs, setLogs] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const params = new URLSearchParams();
        if (filters.user) params.set("user_filter", filters.user);
        if (filters.action) params.set("action", filters.action);
        setIsLoading(true);
        fetch(`/api/audit?${params.toString()}`)
            .then(async (response) => {
                const data = await response.json().catch(() => []);
                if (!response.ok) throw new Error(data.message || "Failed to load audit log");
                setLogs(Array.isArray(data) ? data : []);
                setError(null);
            })
            .catch((err) => {
                setLogs([]);
                setError(err.message || "Failed to load audit log");
            })
            .finally(() => setIsLoading(false));
    }, [filters.action, filters.user]);

    const columns = [
        { key: "date", header: "Date", render: (row) => formatDateTime(row.created_at) },
        { key: "user", header: "User", render: (row) => row.user_name || "System" },
        { key: "action", header: "Action", render: (row) => row.action },
        { key: "reference", header: "Entity", render: (row) => row.entity_id || row.entity_type || "n/a" },
        { key: "details", header: "Details", render: (row) => row.details || "n/a" },
        { key: "ip", header: "IP Address", render: (row) => row.ip_address || "n/a" },
    ];

    const exportToCsv = () => {
        const header = ["Date", "User", "Action", "Entity", "Details", "IP Address"];
        const rows = logs.map((entry) => [entry.created_at, entry.user_name || "System", entry.action, entry.entity_id || entry.entity_type || "", entry.details || "", entry.ip_address || ""]);
        const csv = [header, ...rows].map((row) => row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(",")).join("\n");
        const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.setAttribute("download", "audit-log-export.csv");
        link.click();
        URL.revokeObjectURL(url);
    };

    const content = useMemo(() => {
        if (isLoading) {
            return (<div className="page-loading">
              <Spinner className="page-loading__spinner"/>
              <p className="page-loading__text">Loading audit events...</p>
            </div>);
        }
        if (error) {
            return <EmptyState title="Audit log unavailable" description={error}/>;
        }
        return <Table columns={columns} data={logs} rowKey={(row) => row.id} emptyMessage="No audit entries match the selected filters."/>;
    }, [error, isLoading, logs]);

    return (<div>
      <PageHeader title="Audit Trail" description="Review system activity, user actions and submission history for accountability." actions={<Button variant="secondary" onClick={exportToCsv} disabled={logs.length === 0}>
            <Download className="audit-page__export-icon"/>
            Export to CSV
          </Button>}/>

      <div className="audit-page__filters">
        <Input label="Filter by user" placeholder="e.g. Naomi" value={filters.user} onChange={(event) => setFilters((current) => ({ ...current, user: event.target.value }))}/>
        <Input label="Filter by action" placeholder="e.g. submitted" value={filters.action} onChange={(event) => setFilters((current) => ({ ...current, action: event.target.value }))}/>
      </div>

      {content}
    </div>);
}
