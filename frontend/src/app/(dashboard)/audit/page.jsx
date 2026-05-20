"use client";
import { Download } from "lucide-react";
import { useMemo, useState } from "react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Table } from "@/components/ui/Table";
import { mockAuditLogs } from "@/lib/mockData";
import { formatDateTime } from "@/lib/utils";
export default function AuditPage() {
    const [filters, setFilters] = useState({
        user: "",
        action: "",
    });
    const filteredLogs = useMemo(() => mockAuditLogs.filter((entry) => {
        const matchesUser = filters.user ? entry.user.toLowerCase().includes(filters.user.toLowerCase()) : true;
        const matchesAction = filters.action ? entry.action.toLowerCase().includes(filters.action.toLowerCase()) : true;
        return matchesUser && matchesAction;
    }), [filters.action, filters.user]);
    const columns = [
        { key: "date", header: "Date", render: (row) => formatDateTime(row.date) },
        { key: "user", header: "User", render: (row) => row.user },
        { key: "action", header: "Action", render: (row) => row.action },
        { key: "reference", header: "Item Reference", render: (row) => row.itemReference },
        { key: "ip", header: "IP Address", render: (row) => row.ipAddress },
    ];
    const exportToCsv = () => {
        const header = ["Date", "User", "Action", "Item Reference", "IP Address"];
        const rows = filteredLogs.map((entry) => [entry.date, entry.user, entry.action, entry.itemReference, entry.ipAddress]);
        const csv = [header, ...rows].map((row) => row.join(",")).join("\n");
        const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.setAttribute("download", "audit-log-export.csv");
        link.click();
        URL.revokeObjectURL(url);
    };
    return (<div>
      <PageHeader title="Audit Trail" description="Review system activity, user actions and submission history for accountability." actions={<Button variant="secondary" onClick={exportToCsv}>
            <Download className="h-4 w-4"/>
            Export to CSV
          </Button>}/>

      <div className="mb-6 grid gap-4 rounded-md border border-[--border] bg-white p-5 shadow-sm md:grid-cols-2">
        <Input label="Filter by user" placeholder="e.g. Naomi" value={filters.user} onChange={(event) => setFilters((current) => ({ ...current, user: event.target.value }))}/>
        <Input label="Filter by action" placeholder="e.g. Submitted question" value={filters.action} onChange={(event) => setFilters((current) => ({ ...current, action: event.target.value }))}/>
      </div>

      <Table columns={columns} data={filteredLogs} rowKey={(row) => row.id} emptyMessage="No audit entries match the selected filters."/>
    </div>);
}
