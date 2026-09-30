"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { User, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Dept = { id: number; name: string };

export default function NewCampaignPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [depts, setDepts] = useState<Dept[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    name: "",
    mode: "poll",
    department_id: "",
    target_user_id: "",
    group_head_id: "",
    identity_mode: "anonymous_result",
    comment_rule: "required",
    rank_direction: "one_is_best",
    allow_employee_results: false,
    reminder_enabled: true,
    start_at: "",
    end_at: "",
    participant_ids: [] as number[],
    grade_employee_ids: [] as number[],
    publish: true,
  });

  useEffect(() => {
    if (!user) return;
    api<Dept[]>("/api/departments").then(setDepts);
    api<User[]>("/api/users").then(setUsers);
  }, [user]);

  function toggleId(key: "participant_ids" | "grade_employee_ids", id: number) {
    setForm((f) => {
      const set = new Set(f[key]);
      if (set.has(id)) set.delete(id);
      else set.add(id);
      return { ...f, [key]: Array.from(set) };
    });
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const payload = {
        name: form.name,
        mode: form.mode,
        department_id: form.department_id ? Number(form.department_id) : null,
        target_user_id: form.mode === "poll" && form.target_user_id ? Number(form.target_user_id) : null,
        group_head_id: form.mode === "grade" && form.group_head_id ? Number(form.group_head_id) : null,
        identity_mode: form.identity_mode,
        comment_rule: form.comment_rule,
        rank_direction: form.rank_direction,
        allow_employee_results: form.allow_employee_results,
        reminder_enabled: form.reminder_enabled,
        start_at: form.start_at ? new Date(form.start_at).toISOString() : null,
        end_at: form.end_at ? new Date(form.end_at).toISOString() : null,
        participant_ids: form.mode === "poll" ? form.participant_ids : [],
        grade_employee_ids: form.mode === "grade" ? form.grade_employee_ids : [],
        publish: form.publish,
      };
      const created = await api<{ id: number }>("/api/campaigns", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      router.push(`/campaigns/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    }
  }

  const leaders = users.filter((u) => u.is_leader || u.role === "employee");
  const heads = users.filter((u) => u.role === "group_head" || u.role === "management" || u.role === "system_admin");
  const employees = users.filter((u) => u.role === "employee" || u.role === "group_head");

  return (
    <AppShell>
      <h1 style={{ fontFamily: "var(--font-display)", color: "var(--teal-deep)" }}>New campaign</h1>
      <form className="panel" onSubmit={onSubmit} style={{ maxWidth: 780 }}>
        {error && <div className="error">{error}</div>}
        <div className="field">
          <label>Campaign name</label>
          <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Production Leader Review - Q4" />
        </div>
        <div className="field">
          <label>Mode</label>
          <select value={form.mode} onChange={(e) => setForm({ ...form, mode: e.target.value })}>
            <option value="poll">Poll + Comment</option>
            <option value="grade">Grade / Ranking</option>
          </select>
        </div>
        <div className="field">
          <label>Department</label>
          <select value={form.department_id} onChange={(e) => setForm({ ...form, department_id: e.target.value })}>
            <option value="">Select…</option>
            {depts.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </div>
        {form.mode === "poll" ? (
          <>
            <div className="field">
              <label>Target leader / person</label>
              <select required value={form.target_user_id} onChange={(e) => setForm({ ...form, target_user_id: e.target.value })}>
                <option value="">Select…</option>
                {leaders.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.full_name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Comment rule</label>
              <select value={form.comment_rule} onChange={(e) => setForm({ ...form, comment_rule: e.target.value })}>
                <option value="required">Required</option>
                <option value="optional">Optional</option>
                <option value="disabled">Disabled</option>
              </select>
            </div>
            <div className="field">
              <label>Participants ({form.participant_ids.length})</label>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, maxHeight: 180, overflow: "auto" }}>
                {employees.map((u) => (
                  <label key={u.id} style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <input type="checkbox" checked={form.participant_ids.includes(u.id)} onChange={() => toggleId("participant_ids", u.id)} />
                    {u.full_name}
                  </label>
                ))}
              </div>
            </div>
          </>
        ) : (
          <>
            <div className="field">
              <label>Group Head</label>
              <select required value={form.group_head_id} onChange={(e) => setForm({ ...form, group_head_id: e.target.value })}>
                <option value="">Select…</option>
                {heads.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.full_name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Rank direction</label>
              <select value={form.rank_direction} onChange={(e) => setForm({ ...form, rank_direction: e.target.value })}>
                <option value="one_is_best">Rank 1 = Highest / Best</option>
                <option value="one_is_lowest">Rank 1 = Lowest</option>
              </select>
            </div>
            <div className="field">
              <label>Employees to rank ({form.grade_employee_ids.length})</label>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, maxHeight: 180, overflow: "auto" }}>
                {employees.map((u) => (
                  <label key={u.id} style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <input type="checkbox" checked={form.grade_employee_ids.includes(u.id)} onChange={() => toggleId("grade_employee_ids", u.id)} />
                    {u.full_name}
                  </label>
                ))}
              </div>
            </div>
          </>
        )}
        <div className="field">
          <label>Identity mode</label>
          <select value={form.identity_mode} onChange={(e) => setForm({ ...form, identity_mode: e.target.value })}>
            <option value="named">Named</option>
            <option value="anonymous_result">Anonymous Result</option>
            <option value="strict_anonymous">Strict Anonymous</option>
          </select>
        </div>
        <div className="field">
          <label>Start</label>
          <input type="datetime-local" required value={form.start_at} onChange={(e) => setForm({ ...form, start_at: e.target.value })} />
        </div>
        <div className="field">
          <label>End</label>
          <input type="datetime-local" required value={form.end_at} onChange={(e) => setForm({ ...form, end_at: e.target.value })} />
        </div>
        <label style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          <input type="checkbox" checked={form.allow_employee_results} onChange={(e) => setForm({ ...form, allow_employee_results: e.target.checked })} />
          Allow employees to view results after close
        </label>
        <label style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          <input type="checkbox" checked={form.publish} onChange={(e) => setForm({ ...form, publish: e.target.checked })} />
          Publish now (schedule / open by time window)
        </label>
        <button className="btn btn-primary" type="submit">
          Create campaign
        </button>
      </form>
    </AppShell>
  );
}
