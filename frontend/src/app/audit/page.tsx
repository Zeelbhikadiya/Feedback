"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function AuditPage() {
  const { user } = useAuth();
  const [audit, setAudit] = useState<any[]>([]);
  const [notes, setNotes] = useState<any[]>([]);

  useEffect(() => {
    if (!user) return;
    api<any[]>("/api/audit").then(setAudit);
    api<any[]>("/api/notifications").then(setNotes);
  }, [user]);

  return (
    <AppShell>
      <h1 style={{ fontFamily: "var(--font-display)", color: "var(--teal-deep)" }}>Audit & notifications</h1>
      <div className="panel" style={{ marginBottom: 12 }}>
        <h3 style={{ marginTop: 0 }}>Audit log</h3>
        <table className="table">
          <thead>
            <tr><th>When</th><th>Actor</th><th>Action</th><th>Entity</th><th>Detail</th></tr>
          </thead>
          <tbody>
            {audit.map((r) => (
              <tr key={r.id}>
                <td>{new Date(r.created_at).toLocaleString()}</td>
                <td>{r.actor_name || r.actor_id}</td>
                <td>{r.action}</td>
                <td>{r.entity_type} {r.entity_id}</td>
                <td>{r.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Notification log</h3>
        <table className="table">
          <thead>
            <tr><th>When</th><th>Campaign</th><th>User</th><th>Subject</th><th>Status</th></tr>
          </thead>
          <tbody>
            {notes.map((r) => (
              <tr key={r.id}>
                <td>{new Date(r.created_at).toLocaleString()}</td>
                <td>{r.campaign_id}</td>
                <td>{r.user_id}</td>
                <td>{r.subject}</td>
                <td>{r.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AppShell>
  );
}
