import { Badge } from "@/components/ui/Badge";
import { Table } from "@/components/ui/Table";
import { getSessionById } from "@/lib/mockData";
import { formatDate } from "@/lib/utils";
const statusVariantMap = {
    Pending: "pending",
    Reviewed: "reviewed",
    Duplicate: "duplicate",
    Clear: "clear",
};
export function RecentActivity({ submissions }) {
    const columns = [
        {
            key: "type",
            header: "Item Type",
            render: (row) => <Badge variant={row.type === "Question" ? "question" : "motion"}>{row.type}</Badge>,
        },
        {
            key: "session",
            header: "Session",
            render: (row) => { var _a, _b; return (_b = (_a = getSessionById(row.sessionId)) === null || _a === void 0 ? void 0 : _a.name) !== null && _b !== void 0 ? _b : "Unknown Session"; },
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
            render: (row) => <Badge variant={statusVariantMap[row.status]}>{row.status}</Badge>,
        },
    ];
    return <Table columns={columns} data={submissions} rowKey={(row) => row.id} emptyMessage="No recent submissions found."/>;
}
