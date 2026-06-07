import { Badge } from "@/components/ui/Badge";
import { Table } from "@/components/ui/Table";
import { formatDate } from "@/lib/utils";
const statusVariantMap = {
    Pending: "pending",
    "Pending Review": "pending",
    Reviewed: "reviewed",
    Duplicate: "duplicate",
    Clear: "clear",
    "Clear (New)": "clear",
    "Substantially Similar": "similar",
    Historical: "reviewed",
};
export function RecentActivity({ submissions, sessions = [] }) {
    const sessionMap = new Map(sessions.map((session) => [session.id, session.name]));
    const columns = [
        {
            key: "type",
            header: "Item Type",
            render: (row) => <Badge variant={row.type === "Question" ? "question" : "motion"}>{row.type}</Badge>,
        },
        {
            key: "session",
            header: "Session",
            render: (row) => sessionMap.get(row.sessionId) || "Unknown Session",
        },
        {
            key: "submittedBy",
            header: "Submitted By",
            render: (row) => row.submittedBy,
        },
        {
            key: "date",
            header: "Date",
            render: (row) => formatDate(row.submittedAt),
        },
        {
            key: "status",
            header: "Status",
            render: (row) => <Badge variant={statusVariantMap[row.status] || "info"}>{row.status}</Badge>,
        },
    ];
    return <Table columns={columns} data={submissions} rowKey={(row) => row.id} emptyMessage="No recent submissions found."/>;
}
