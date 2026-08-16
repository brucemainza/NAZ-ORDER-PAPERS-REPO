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
import { mockUsers } from "@/lib/mockData";
import { formatDateTime } from "@/lib/utils";
export default function UsersPage() {
    const { user, isLoading } = useAuth();
    const [users, setUsers] = useState(mockUsers);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [formValues, setFormValues] = useState({
        name: "",
        employeeId: "",
        role: "Clerk",
        status: "Active",
    });
    const columns = [
        { key: "name", header: "Name", render: (row) => row.name },
        { key: "employeeId", header: "Employee ID", render: (row) => row.employeeId },
        {
            key: "role",
            header: "Role",
            render: (row) => (<Badge variant={row.role === "Admin" ? "admin" : row.role === "Senior Clerk" ? "seniorClerk" : "clerk"}>{row.role}</Badge>),
        },
        { key: "status", header: "Status", render: (row) => <Badge variant={row.status === "Active" ? "active" : "inactive"}>{row.status}</Badge> },
        { key: "lastLogin", header: "Last Login", render: (row) => formatDateTime(row.lastLogin) },
        {
            key: "actions",
            header: "Actions",
            render: () => (<div className="users-page__actions">
          <Button variant="secondary" size="sm">
            Edit Role
          </Button>
          <Button variant="ghost" size="sm">
            Reset Invite
          </Button>
        </div>),
        },
    ];
    if (!isLoading && !hasPermission(user, "manage_users")) {
        return (<div>
        <PageHeader title="Users" description="Manage internal user accounts, roles and access status."/>
        <EmptyState title="Access denied" description="You do not have permission to manage user accounts."/>
      </div>);
    }
    return (<div>
      <PageHeader title="Users" description="Manage authorised staff accounts, role assignment and account status." actions={<Button onClick={() => setIsModalOpen(true)}>Invite User</Button>}/>

      <Table columns={columns} data={users} rowKey={(row) => row.id} emptyMessage="No users have been added yet."/>
      <p className="users-page__count">Showing {users.length} of {users.length} authorised users</p>

      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Invite User" description="Create a placeholder account for a new authorised staff member." footer={<>
            <Button variant="secondary" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => {
                const newUser = {
                    id: `user-local-${Date.now()}`,
                    name: formValues.name,
                    employeeId: formValues.employeeId,
                    role: formValues.role,
                    status: formValues.status,
                    lastLogin: new Date().toISOString(),
                };
                setUsers((current) => [newUser, ...current]);
                setFormValues({ name: "", employeeId: "", role: "Clerk", status: "Active" });
                setIsModalOpen(false);
            }}>
              Save User
            </Button>
          </>}>
        <div className="users-page__form">
          <Input label="Full Name" value={formValues.name} onChange={(event) => setFormValues((current) => ({ ...current, name: event.target.value }))}/>
          <Input label="Employee ID" value={formValues.employeeId} onChange={(event) => setFormValues((current) => ({ ...current, employeeId: event.target.value }))}/>
          <Select label="Role" value={formValues.role} onChange={(event) => setFormValues((current) => ({ ...current, role: event.target.value }))}>
            <option value="Admin">Admin</option>
            <option value="Senior Clerk">Senior Clerk</option>
            <option value="Clerk">Clerk</option>
          </Select>
          <Select label="Status" value={formValues.status} onChange={(event) => setFormValues((current) => ({ ...current, status: event.target.value }))}>
            <option value="Active">Active</option>
            <option value="Inactive">Inactive</option>
          </Select>
        </div>
      </Modal>
    </div>);
}
