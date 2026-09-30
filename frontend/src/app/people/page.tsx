"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { User, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Dept = { id: number; name: string; code?: string };

export default function PeoplePage() {
  const { user } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [depts, setDepts] = useState<Dept[]>([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    email: "",
    full_name: "",
    password: "Password123!",
    role: "employee",
    department_id: "",
    is_leader: false,
  });
  const [deptName, setDeptName] = useState("");

  function reload() {
    api<User[]>("/api/users").then(setUsers);
    api<Dept[]>("/api/departments").then(setDepts);
  }

  useEffect(() => {
    if (user) reload();
  }, [user]);

  async function createUser(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api("/api/users", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          department_id: form.department_id ? Number(form.department_id) : null,
        }),
      });
      setForm({ ...form, email: "", full_name: "" });
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    }
  }

  async function createDept(e: FormEvent) {
    e.preventDefault();
    await api("/api/departments", { method: "POST", body: JSON.stringify({ name: deptName }) });
    setDeptName("");
    reload();
  }

  async function deactivate(id: number) {
    await api(`/api/users/${id}`, { method: "PATCH", body: JSON.stringify({ is_active: false }) });
    reload();
  }

  return (
    <AppShell>
      <h1 style={{ fontFamily: "var(--font-display)", color: "var(--teal-deep)" }}>People & organization</h1>
      {error && <div className="error">{error}</div>}
      <div className="grid-3" style={{ marginBottom: 12 }}>
        <form className="panel" onSubmit={createDept}>
          <h3 style={{ marginTop: 0 }}>Add department</h3>
          <div className="field">
            <label>Name</label>
            <input value={deptName} onChange={(e) => setDeptName(e.target.value)} required />
          </div>
          <button className="btn btn-primary">Add</button>
          <ul>
            {depts.map((d) => (
              <li key={d.id}>{d.name}</li>
            ))}
          </ul>
        </form>
        <form className="panel" onSubmit={createUser} style={{ gridColumn: "span 2" }}>
          <h3 style={{ marginTop: 0 }}>Add user</h3>
          <div className="field"><label>Full name</label><input required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></div>
          <div className="field"><label>Email</label><input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
          <div className="field"><label>Role</label>
            <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
              <option value="employee">Employee</option>
              <option value="group_head">Group Head</option>
              <option value="management">Management</option>
              <option value="result_viewer">Result Viewer</option>
              <option value="system_admin">System Admin</option>
            </select>
          </div>
          <div className="field"><label>Department</label>
            <select value={form.department_id} onChange={(e) => setForm({ ...form, department_id: e.target.value })}>
              <option value="">None</option>
              {depts.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          </div>
          <label style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            <input type="checkbox" checked={form.is_leader} onChange={(e) => setForm({ ...form, is_leader: e.target.checked })} />
            Mark as leader (poll target)
          </label>
          <button className="btn btn-primary">Create user</button>
        </form>
      </div>
      <div className="panel">
        <table className="table">
          <thead>
            <tr><th>Name</th><th>Email</th><th>Role</th><th>Leader</th><th>Active</th><th /></tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.full_name}</td>
                <td>{u.email}</td>
                <td>{u.role}</td>
                <td>{u.is_leader ? "Yes" : "—"}</td>
                <td>{u.is_active ? "Yes" : "No"}</td>
                <td>{u.is_active && <button className="btn btn-ghost" onClick={() => deactivate(u.id)}>Deactivate</button>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AppShell>
  );
}
