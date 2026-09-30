"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { Campaign, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function TasksPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<Campaign[]>([]);

  useEffect(() => {
    if (!user) return;
    api<Campaign[]>("/api/campaigns?mine=true").then(setItems);
  }, [user]);

  return (
    <AppShell>
      <h1 style={{ fontFamily: "var(--font-display)", color: "var(--teal-deep)" }}>My tasks</h1>
      <div className="panel">
        <table className="table">
          <thead>
            <tr>
              <th>Campaign</th>
              <th>Mode</th>
              <th>Status</th>
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
                <td>
                  <Link className="btn btn-primary" href={c.mode === "poll" ? `/poll/${c.id}` : `/grade/${c.id}`}>
                    Continue
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {items.length === 0 && <p className="muted">No assigned campaigns.</p>}
      </div>
    </AppShell>
  );
}
