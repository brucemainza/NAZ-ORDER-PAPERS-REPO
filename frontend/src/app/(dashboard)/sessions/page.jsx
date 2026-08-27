"use client";
import { useState } from "react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { Table } from "@/components/ui/Table";
import { useAuth } from "@/hooks/useAuth";
import { hasPermission } from "@/lib/auth";
import { mockSessions } from "@/lib/mockData";
import { formatDate } from "@/lib/utils";
export default function SessionsPage() {
    const { user, isLoading } = useAuth();
    const [sessions, setSessions] = useState(mockSessions);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [formValues, setFormValues] = useState({
        name: "",
        startDate: "",
        endDate: "",
        status: "Upcoming",
    });
    const columns = [
        { key: "name", header: "Session Name", render: (row) => row.name },
        { key: "startDate", header: "Start Date", render: (row) => formatDate(row.startDate) },
        { key: "endDate", header: "End Date", render: (row) => formatDate(row.endDate) },
        { key: "status", header: "Status", render: (row) => <Badge variant={row.status.toLowerCase()}>{row.status}</Badge> },
        {
            key: "actions",
            header: "Actions",
            render: (row) => (<div className="sessions-page__actions">
          <Button variant="secondary" size="sm">
            Edit
          </Button>
          {row.status === "Active" ? <Button variant="ghost" size="sm">
            Close
          </Button> : null}
        </div>),
        },
    ];
    if (!isLoading && !hasPermission(user, "manage_sessions")) {
        return (<div>
        <PageHeader title="Parliamentary Sessions" description="Manage active, closed and upcoming parliamentary sessions."/>
        <EmptyState title="Access denied" description="You do not have permission to manage parliamentary sessions."/>
      </div>);
    }
    return (<div className="sessions-page">
      <PageHeader title="Parliamentary Sessions" actions={<Button onClick={() => setIsModalOpen(true)}>Add Session</Button>}/>

      <Table columns={columns} data={sessions} rowKey={(row) => row.id} emptyMessage="No sessions have been configured."/>

      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Add Session" description="Create a new parliamentary session entry for future submissions." footer={<>
            <Button variant="secondary" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => {
                const newSession = {
                    id: `session-local-${Date.now()}`,
                    name: formValues.name,
                    startDate: formValues.startDate,
                    endDate: formValues.endDate,
                    status: formValues.status,
                };
                setSessions((current) => [newSession, ...current]);
                setFormValues({ name: "", startDate: "", endDate: "", status: "Upcoming" });
                setIsModalOpen(false);
            }}>
              Save Session
            </Button>
          </>}>
        <div className="sessions-page__form">
          <Input label="Session Name" value={formValues.name} onChange={(event) => setFormValues((current) => ({ ...current, name: event.target.value }))}/>
          <div className="sessions-page__dates">
            <Input label="Start Date" type="date" value={formValues.startDate} onChange={(event) => setFormValues((current) => ({ ...current, startDate: event.target.value }))}/>
            <Input label="End Date" type="date" value={formValues.endDate} onChange={(event) => setFormValues((current) => ({ ...current, endDate: event.target.value }))}/>
          </div>
          <Select label="Status" value={formValues.status} onChange={(event) => setFormValues((current) => ({ ...current, status: event.target.value }))}>
            <option value="Upcoming">Upcoming</option>
            <option value="Active">Active</option>
            <option value="Closed">Closed</option>
          </Select>
        </div>
      </Modal>
    </div>);
}
