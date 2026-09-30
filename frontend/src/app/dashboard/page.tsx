"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { Campaign, api } from "@/lib/api";
import { isManager, useAuth } from "@/lib/auth";
import { Locale, t } from "@/lib/i18n";

type Dash = {
  active: Campaign[];
  scheduled: Campaign[];
  recently_closed: Campaign[];
  totals: Record<string, number>;
};

export default function DashboardPage() {
  const { user } = useAuth();
  const locale = (user?.locale as Locale) || "en";
  const [data, setData] = useState<Dash | null>(null);
  const [mine, setMine] = useState<Campaign[]>([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!user) return;
    if (isManager(user.role) || user.role === "result_viewer") {
      api<Dash>("/api/campaigns/dashboard")
        .then(setData)
        .catch((e) => setErr(e.message));
    }
    api<Campaign[]>("/api/campaigns?mine=true")
      .then(setMine)
      .catch(() => undefined);
  }, [user]);

  return (
    <AppShell>
      <div className="topbar">
        <div>
          <h1 style={{ margin: 0, fontFamily: "var(--font-display)", fontSize: "2rem", color: "var(--teal-deep)" }}>
            {t(locale, "dashboard")}
          </h1>
          <p className="muted" style={{ margin: "0.35rem 0 0" }}>
            Active campaigns, schedules and your assigned work.
          </p>
        </div>
        {isManager(user?.role) && (
          <Link className="btn btn-primary" href="/campaigns/new">
            {t(locale, "createCampaign")}
          </Link>
        )}
      </div>

      {err && <div className="error">{err}</div>}

      {data && (
        <div className="grid-3" style={{ marginBottom: "1rem" }}>
          <div className="panel stat">
            <h3>Active</h3>
            <p>{data.totals.active}</p>
          </div>
          <div className="panel stat">
            <h3>Scheduled</h3>
            <p>{data.totals.scheduled}</p>
          </div>
          <div className="panel stat">
            <h3>Recently closed</h3>
            <p>{data.totals.closed}</p>
          </div>
        </div>
      )}

      <div className="panel" style={{ marginBottom: "1rem" }}>
        <h2 style={{ marginTop: 0 }}>{t(locale, "myTasks")}</h2>
        {mine.length === 0 ? (
          <p className="muted">No assigned campaigns right now.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Mode</th>
                <th>Status</th>
                <th>Closes</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {mine.map((c) => (
                <tr key={c.id}>
                  <td>{c.name}</td>
                  <td>{c.mode}</td>
                  <td>
                    <span className={`badge ${c.status}`}>{c.status}</span>
                  </td>
                  <td>{c.end_at ? new Date(c.end_at).toLocaleString() : "—"}</td>
                  <td>
                    <Link href={c.mode === "poll" ? `/poll/${c.id}` : `/grade/${c.id}`}>Open</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {data && (
        <div className="panel">
          <h2 style={{ marginTop: 0 }}>Active campaigns</h2>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Dept</th>
                <th>Progress</th>
                <th>End</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.active.map((c) => (
                <tr key={c.id}>
                  <td>{c.name}</td>
                  <td>{c.department_name || "—"}</td>
                  <td>
                    {c.submitted_count}/{c.participant_count}
                  </td>
                  <td>{c.end_at ? new Date(c.end_at).toLocaleString() : "—"}</td>
                  <td>
                    <Link href={`/campaigns/${c.id}`}>View</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </AppShell>
  );
}
