"use client";
import { useEffect, useState } from "react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { Spinner } from "@/components/ui/Spinner";
import { Table } from "@/components/ui/Table";
import { Toast } from "@/components/ui/Toast";
import { useAuth } from "@/hooks/useAuth";
import { hasPermission } from "@/lib/auth";
import { formatDate } from "@/lib/utils";

const emptyForm = { code: "", name: "", startDate: "", endDate: "", status: "Upcoming" };

export default function SessionsPage() {
    const { user, isLoading: isAuthLoading } = useAuth();
    const [sessions, setSessions] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [loadError, setLoadError] = useState(null);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingSession, setEditingSession] = useState(null);
    const [formValues, setFormValues] = useState(emptyForm);
    const [actionError, setActionError] = useState(null);
    const [pendingActionId, setPendingActionId] = useState(null);

    function loadSessions() {
        setIsLoading(true);
        fetch("/api/sessions")
            .then(async (response) => {
                const data = await response.json().catch(() => []);
                if (!response.ok) throw new Error(data.message || "Could not load sessions");
                setSessions(Array.isArray(data) ? data : []);
                setLoadError(null);
            })
            .catch((requestError) => {
                setSessions([]);
                setLoadError(requestError.message || "Could not load sessions");
            })
            .finally(() => setIsLoading(false));
    }

    useEffect(() => {
        loadSessions();
    }, []);

    function openEditModal(session) {
        setEditingSession(session);
        setFormValues({
            code: session.code,
            name: session.name,
            startDate: session.start_date,
            endDate: session.end_date,
            status: session.status,
        });
        setActionError(null);
        setIsModalOpen(true);
    }

    function openCreateModal() {
        setEditingSession(null);
        setFormValues(emptyForm);
        setActionError(null);
        setIsModalOpen(true);
    }

    function closeModal() {
        setIsModalOpen(false);
        setEditingSession(null);
        setFormValues(emptyForm);
        setActionError(null);
    }

    async function saveSession() {
        if (!editingSession) return;
        setPendingActionId(editingSession.id);
        setActionError(null);
        try {
            const response = await fetch(`/api/sessions/${editingSession.id}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: formValues.name,
                    start_date: formValues.startDate,
                    end_date: formValues.endDate,
                    status: formValues.status,
                }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(data.message || "Could not update session");
            setSessions((current) => current.map((item) => (item.id === data.id ? data : item)));
            closeModal();
        } catch (saveError) {
            setActionError(saveError.message || "Could not update session");
        } finally {
            setPendingActionId(null);
        }
    }

    async function createSession() {
        setPendingActionId("new");
        setActionError(null);
        try {
            const response = await fetch("/api/sessions", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    code: formValues.code,
                    name: formValues.name,
                    start_date: formValues.startDate,
                    end_date: formValues.endDate,
                    status: formValues.status,
                }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(data.message || "Could not create session");
            setSessions((current) => [data, ...current]);
            closeModal();
        } catch (createError) {
            setActionError(createError.message || "Could not create session");
        } finally {
            setPendingActionId(null);
        }
    }

    async function updateStatus(session, status) {
        setPendingActionId(session.id);
        setLoadError(null);
        try {
            const response = await fetch(`/api/sessions/${session.id}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ status }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(data.message || "Could not update session");
            setSessions((current) => current.map((item) => (item.id === data.id ? data : item)));
        } catch (statusError) {
            setLoadError(statusError.message || "Could not update session");
        } finally {
            setPendingActionId(null);
        }
    }

    async function deleteSession(session) {
        if (!window.confirm(`Delete "${session.name}"? This cannot be undone.`)) {
            return;
        }
        setPendingActionId(session.id);
        setLoadError(null);
        try {
            const response = await fetch(`/api/sessions/${session.id}`, { method: "DELETE" });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(data.message || "Could not delete session");
            setSessions((current) => current.filter((item) => item.id !== session.id));
        } catch (deleteError) {
            setLoadError(deleteError.message || "Could not delete session");
        } finally {
            setPendingActionId(null);
        }
    }

    const columns = [
        { key: "name", header: "Session Name", render: (row) => row.name },
        { key: "startDate", header: "Start Date", render: (row) => formatDate(row.start_date) },
        { key: "endDate", header: "End Date", render: (row) => formatDate(row.end_date) },
        { key: "status", header: "Status", render: (row) => <Badge variant={row.status.toLowerCase()}>{row.status}</Badge> },
        {
            key: "actions",
            header: "Actions",
            render: (row) => (<div className="sessions-page__actions">
          <Button variant="secondary" size="sm" onClick={() => openEditModal(row)} disabled={pendingActionId === row.id}>
            Edit
          </Button>
          {row.status === "Active" ? (<Button variant="ghost" size="sm" onClick={() => updateStatus(row, "Closed")} disabled={pendingActionId === row.id}>
            Close
          </Button>) : (<Button variant="ghost" size="sm" onClick={() => updateStatus(row, "Active")} disabled={pendingActionId === row.id}>
            Activate
          </Button>)}
          <Button variant="ghost" size="sm" onClick={() => deleteSession(row)} disabled={pendingActionId === row.id}>
            Delete
          </Button>
        </div>),
        },
    ];

    if (!isAuthLoading && !hasPermission(user, "manage_sessions")) {
        return (<div>
        <PageHeader title="Parliamentary Sessions" description="Manage active, closed and upcoming parliamentary sessions."/>
        <EmptyState title="Access denied" description="You do not have permission to manage parliamentary sessions."/>
      </div>);
    }

    return (<div className="sessions-page">
      <PageHeader title="Parliamentary Sessions" actions={<Button onClick={openCreateModal}>New Session</Button>}/>

      {loadError ? <Toast variant="error" title="Session action failed" description={loadError}/> : null}

      {isLoading ? (<div className="page-loading">
          <Spinner className="page-loading__spinner"/>
          <p className="page-loading__text">Loading sessions...</p>
        </div>) : (<Table columns={columns} data={sessions} rowKey={(row) => row.id} emptyMessage="No sessions have been configured."/>)}

      <Modal isOpen={isModalOpen} onClose={closeModal} title={editingSession ? "Edit Session" : "New Session"} description={editingSession ? "Update this parliamentary session's details." : "Create a new parliamentary session."} footer={<>
            <Button variant="secondary" onClick={closeModal}>
              Cancel
            </Button>
            <Button onClick={editingSession ? saveSession : createSession} disabled={pendingActionId === (editingSession?.id ?? "new")}>
              {editingSession ? "Save Changes" : "Create Session"}
            </Button>
          </>}>
        {actionError ? <Toast variant="error" title={editingSession ? "Could not save session" : "Could not create session"} description={actionError}/> : null}
        <div className="sessions-page__form">
          {!editingSession ? (
            <Input label="Session Code" placeholder="session-13-2027" value={formValues.code} onChange={(event) => setFormValues((current) => ({ ...current, code: event.target.value }))}/>
          ) : null}
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
