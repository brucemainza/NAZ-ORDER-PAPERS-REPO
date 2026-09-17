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
import { formatDateTime } from "@/lib/utils";

const emptyAddForm = { employeeId: "", name: "", roleName: "", status: "Active" };

function roleBadgeVariant(role) {
    if (role === "Administrator") return "admin";
    if (role === "Clerk") return "clerk";
    return "info";
}

export default function UsersPage() {
    const { user, isLoading: isAuthLoading } = useAuth();
    const [users, setUsers] = useState([]);
    const [roles, setRoles] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [loadError, setLoadError] = useState(null);
    const [pendingUserId, setPendingUserId] = useState(null);

    const [isAddModalOpen, setIsAddModalOpen] = useState(false);
    const [addForm, setAddForm] = useState(emptyAddForm);
    const [addError, setAddError] = useState(null);

    const [roleTarget, setRoleTarget] = useState(null);
    const [roleFormValue, setRoleFormValue] = useState("");
    const [roleError, setRoleError] = useState(null);

    const [credentials, setCredentials] = useState(null);

    function loadData() {
        setIsLoading(true);
        Promise.all([
            fetch("/api/users").then((response) => response.json().catch(() => []).then((data) => ({ response, data }))),
            fetch("/api/roles").then((response) => response.json().catch(() => []).then((data) => ({ response, data }))),
        ])
            .then(([usersResult, rolesResult]) => {
                if (!usersResult.response.ok) throw new Error(usersResult.data.message || "Could not load users");
                if (!rolesResult.response.ok) throw new Error(rolesResult.data.message || "Could not load roles");
                setUsers(Array.isArray(usersResult.data) ? usersResult.data : []);
                setRoles(Array.isArray(rolesResult.data) ? rolesResult.data : []);
                setLoadError(null);
            })
            .catch((requestError) => {
                setUsers([]);
                setLoadError(requestError.message || "Could not load users");
            })
            .finally(() => setIsLoading(false));
    }

    useEffect(() => {
        loadData();
    }, []);

    function openAddModal() {
        setAddForm({ ...emptyAddForm, roleName: roles[0] || "" });
        setAddError(null);
        setIsAddModalOpen(true);
    }

    function closeAddModal() {
        setIsAddModalOpen(false);
        setAddForm(emptyAddForm);
        setAddError(null);
    }

    async function createUser() {
        setPendingUserId("new");
        setAddError(null);
        try {
            const response = await fetch("/api/users", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    employee_id: addForm.employeeId,
                    name: addForm.name,
                    role_name: addForm.roleName,
                    status: addForm.status,
                }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(data.message || "Could not create user");
            setUsers((current) => [data.user, ...current]);
            closeAddModal();
            setCredentials({
                title: "User created",
                employeeId: data.user.employee_id,
                password: data.temporary_password,
            });
        } catch (createError) {
            setAddError(createError.message || "Could not create user");
        } finally {
            setPendingUserId(null);
        }
    }

    function openRoleModal(target) {
        setRoleTarget(target);
        setRoleFormValue(target.role);
        setRoleError(null);
    }

    function closeRoleModal() {
        setRoleTarget(null);
        setRoleFormValue("");
        setRoleError(null);
    }

    async function saveRole() {
        if (!roleTarget) return;
        setPendingUserId(roleTarget.id);
        setRoleError(null);
        try {
            const response = await fetch(`/api/users/${roleTarget.id}/role`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ role_name: roleFormValue }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(data.message || "Could not update role");
            setUsers((current) => current.map((item) => (item.id === data.id ? { ...item, role: data.role } : item)));
            closeRoleModal();
        } catch (saveError) {
            setRoleError(saveError.message || "Could not update role");
        } finally {
            setPendingUserId(null);
        }
    }

    async function resetPassword(target) {
        if (!window.confirm(`Reset the password for ${target.name}? Their current password will stop working immediately.`)) {
            return;
        }
        setPendingUserId(target.id);
        setLoadError(null);
        try {
            const response = await fetch(`/api/users/${target.id}/reset-password`, { method: "POST" });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(data.message || "Could not reset password");
            setCredentials({
                title: "Password reset",
                employeeId: target.employee_id,
                password: data.temporary_password,
            });
        } catch (resetError) {
            setLoadError(resetError.message || "Could not reset password");
        } finally {
            setPendingUserId(null);
        }
    }

    const columns = [
        { key: "name", header: "Name", render: (row) => row.name },
        { key: "employee_id", header: "Employee ID", render: (row) => row.employee_id },
        { key: "role", header: "Role", render: (row) => <Badge variant={roleBadgeVariant(row.role)}>{row.role}</Badge> },
        { key: "status", header: "Status", render: (row) => <Badge variant={row.status === "Active" ? "active" : "inactive"}>{row.status}</Badge> },
        { key: "last_login_at", header: "Last Login", render: (row) => (row.last_login_at ? formatDateTime(row.last_login_at) : "Never") },
        {
            key: "actions",
            header: "Actions",
            render: (row) => (<div className="users-page__actions">
          <Button variant="secondary" size="sm" onClick={() => openRoleModal(row)} disabled={pendingUserId === row.id}>
            Edit Role
          </Button>
          <Button variant="ghost" size="sm" onClick={() => resetPassword(row)} disabled={pendingUserId === row.id}>
            Reset Password
          </Button>
        </div>),
        },
    ];

    if (!isAuthLoading && !hasPermission(user, "manage_users")) {
        return (<div>
        <PageHeader title="Users" description="Manage internal user accounts, roles and access status."/>
        <EmptyState title="Access denied" description="You do not have permission to manage user accounts."/>
      </div>);
    }

    return (<div>
      <PageHeader title="Users" description="Manage authorised staff accounts, role assignment and account status." actions={<Button onClick={openAddModal}>Add User</Button>}/>

      {loadError ? <Toast variant="error" title="User action failed" description={loadError}/> : null}

      {isLoading ? (<div className="page-loading">
          <Spinner className="page-loading__spinner"/>
          <p className="page-loading__text">Loading users...</p>
        </div>) : (<>
          <Table columns={columns} data={users} rowKey={(row) => row.id} emptyMessage="No users have been added yet."/>
          <p className="users-page__count">Showing {users.length} of {users.length} authorised users</p>
        </>)}

      <Modal isOpen={isAddModalOpen} onClose={closeAddModal} title="Add User" description="Create a new authorised staff account with a system-generated temporary password." footer={<>
            <Button variant="secondary" onClick={closeAddModal}>
              Cancel
            </Button>
            <Button onClick={createUser} disabled={pendingUserId === "new"}>
              {pendingUserId === "new" ? "Creating..." : "Create User"}
            </Button>
          </>}>
        {addError ? <Toast variant="error" title="Could not create user" description={addError}/> : null}
        <div className="users-page__form">
          <Input label="Full Name" value={addForm.name} onChange={(event) => setAddForm((current) => ({ ...current, name: event.target.value }))}/>
          <Input label="Employee ID" value={addForm.employeeId} onChange={(event) => setAddForm((current) => ({ ...current, employeeId: event.target.value }))}/>
          <Select label="Role" value={addForm.roleName} onChange={(event) => setAddForm((current) => ({ ...current, roleName: event.target.value }))}>
            {roles.map((roleName) => (<option key={roleName} value={roleName}>{roleName}</option>))}
          </Select>
          <Select label="Status" value={addForm.status} onChange={(event) => setAddForm((current) => ({ ...current, status: event.target.value }))}>
            <option value="Active">Active</option>
            <option value="Inactive">Inactive</option>
          </Select>
        </div>
      </Modal>

      <Modal isOpen={Boolean(roleTarget)} onClose={closeRoleModal} title="Edit Role" description={roleTarget ? `Change the permission role assigned to ${roleTarget.name}.` : ""} footer={<>
            <Button variant="secondary" onClick={closeRoleModal}>
              Cancel
            </Button>
            <Button onClick={saveRole} disabled={pendingUserId === roleTarget?.id}>
              {pendingUserId === roleTarget?.id ? "Saving..." : "Save Role"}
            </Button>
          </>}>
        {roleError ? <Toast variant="error" title="Could not update role" description={roleError}/> : null}
        <div className="users-page__form">
          <Select label="Role" value={roleFormValue} onChange={(event) => setRoleFormValue(event.target.value)}>
            {roles.map((roleName) => (<option key={roleName} value={roleName}>{roleName}</option>))}
          </Select>
        </div>
      </Modal>

      <Modal isOpen={Boolean(credentials)} onClose={() => setCredentials(null)} title={credentials?.title || ""} description="This password is shown once. Share it with the staff member through a secure channel — it cannot be retrieved again." footer={<Button onClick={() => setCredentials(null)}>Done</Button>}>
        {credentials ? (<div className="users-page__form">
            <p><strong>Employee ID:</strong> {credentials.employeeId}</p>
            <p><strong>Temporary password:</strong> <code>{credentials.password}</code></p>
          </div>) : null}
      </Modal>
    </div>);
}
