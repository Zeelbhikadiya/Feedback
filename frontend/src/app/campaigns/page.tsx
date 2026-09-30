"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { Campaign, api } from "@/lib/api";
import { isManager, useAuth } from "@/lib/auth";

export default function CampaignsPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<Campaign[]>([]);
  const [mode, setMode] = useState("");
  const [status, setStatus] = useState("");
  const [err, setErr] = useState("");

  function load() {
    const q = new URLSearchParams();
    if (mode) q.set("mode", mode);
    if (status) q.set("status", status);
    api<Campaign[]>(`/api/campaigns?${q}`)
      .then(setItems)
      .catch((e) => setErr(e.message));
  }

  useEffect(() => {
    if (user) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, mode, status]);

  return (
    <AppShell>
      <div className="topbar">
        <h1 style={{ margin: 0, fontFamily: "var(--font-display)", color: "var(--teal-deep)" }}>Campaigns</h1>
        {isManager(user?.role) && (
          <Link className="btn btn-primary" href="/campaigns/new">
            New campaign
          </Link>
        )}
      </div>
      {err && <div className="error">{err}</div>}
      <div className="panel" style={{ marginBottom: "1rem", display: "flex", gap: 12 }}>
        <select value={mode} onChange={(e) => setMode(e.target.value)}>
          <option value="">All modes</option>
          <option value="poll">Poll</option>
          <option value="grade">Grade</option>
        </select>
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          <option value="draft">Draft</option>
          <option value="scheduled">Scheduled</option>
          <option value="open">Open</option>
          <option value="analysis_ready">Analysis ready</option>
          <option value="archived">Archived</option>
        </select>
      </div>
      <div className="panel">
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Mode</th>
              <th>Status</th>
              <th>Target / Head</th>
              <th>Identity</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((c) => (
              <tr key={c.id}>
                <td>{c.name}</td>
                <td>{c.mode}</td>
                <td>
                  <span className={`badge ${c.status}`}>{c.status}</span>
                </td>
                <td>{c.target_name || c.group_head_name || "—"}</td>
                <td>{c.identity_mode}</td>
                <td>
                  <Link href={`/campaigns/${c.id}`}>Open</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AppShell>
  );
}
