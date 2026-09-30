"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AppShell } from "@/components/AppShell";
import { Campaign, api, downloadAuth } from "@/lib/api";
import { isManager, useAuth } from "@/lib/auth";

type PollResult = {
  invited: number;
  submitted: number;
  pending: number;
  response_rate: number;
  average_score: number | null;
  median_score: number | null;
  distribution: Record<string, number>;
  star_average: number | null;
  comment_count: number;
  theme_summary: any;
  ai_summary: string | null;
  comments: { score: number; comment?: string; respondent_name?: string }[];
};

type GradeResult = {
  is_final: boolean;
  ranked_count: number;
  total_required: number;
  ranking: { employee_name: string; rank: number | null }[];
};

export default function CampaignDetailPage() {
  const params = useParams();
  const id = Number(params.id);
  const { user } = useAuth();
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [poll, setPoll] = useState<PollResult | null>(null);
  const [grade, setGrade] = useState<GradeResult | null>(null);
  const [pending, setPending] = useState<any>(null);
  const [trends, setTrends] = useState<any[]>([]);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  async function load() {
    const c = await api<Campaign>(`/api/campaigns/${id}`);
    setCampaign(c);
    try {
      if (c.mode === "poll") {
        const r = await api<PollResult>(`/api/campaigns/${id}/results/poll`);
        setPoll(r);
        if (c.target_user_id) {
          const tr = await api<any[]>(`/api/campaigns/trends/${c.target_user_id}`);
          setTrends(tr);
        }
      } else {
        const r = await api<GradeResult>(`/api/campaigns/${id}/results/grade`);
        setGrade(r);
      }
      if (isManager(user?.role)) {
        const p = await api(`/api/campaigns/${id}/pending`);
        setPending(p);
      }
    } catch {
      // results may be restricted
    }
  }

  useEffect(() => {
    if (user && id) load().catch((e) => setErr(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, id]);

  const chartData = useMemo(() => {
    if (!poll) return [];
    return Object.entries(poll.distribution).map(([score, votes]) => ({ score, votes }));
  }, [poll]);

  async function act(path: string, label: string) {
    setMsg("");
    setErr("");
    try {
      await api(`/api/campaigns/${id}${path}`, { method: "POST" });
      setMsg(label);
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Action failed");
    }
  }

  if (!campaign) {
    return (
      <AppShell>
        <div className="panel">{err || "Loading…"}</div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="topbar">
        <div>
          <h1 style={{ margin: 0, fontFamily: "var(--font-display)", color: "var(--teal-deep)" }}>{campaign.name}</h1>
          <p className="muted">
            {campaign.mode} · <span className={`badge ${campaign.status}`}>{campaign.status}</span> · {campaign.identity_mode}
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {campaign.mode === "poll" ? (
            <Link className="btn btn-ghost" href={`/poll/${id}`}>
              Open poll form
            </Link>
          ) : (
            <Link className="btn btn-ghost" href={`/grade/${id}`}>
              Open ranking
            </Link>
          )}
          <button className="btn btn-ghost" onClick={() => downloadAuth(`/api/campaigns/${id}/calendar.ics`, `campaign_${id}.ics`)}>
            Calendar .ics
          </button>
        </div>
      </div>

      {msg && <div className="panel" style={{ marginBottom: 12, borderColor: "#1f7a4c" }}>{msg}</div>}
      {err && <div className="error">{err}</div>}

      <div className="grid-3" style={{ marginBottom: 12 }}>
        <div className="panel">
          <div className="muted">Department</div>
          <strong>{campaign.department_name || "—"}</strong>
        </div>
        <div className="panel">
          <div className="muted">{campaign.mode === "poll" ? "Target" : "Group Head"}</div>
          <strong>{campaign.target_name || campaign.group_head_name || "—"}</strong>
        </div>
        <div className="panel">
          <div className="muted">Window</div>
          <strong style={{ fontSize: 14 }}>
            {campaign.start_at ? new Date(campaign.start_at).toLocaleString() : "—"}
            <br />→ {campaign.end_at ? new Date(campaign.end_at).toLocaleString() : "—"}
          </strong>
        </div>
      </div>

      {isManager(user?.role) && (
        <div className="panel" style={{ marginBottom: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button className="btn btn-ghost" onClick={() => act("/publish", "Published")}>Publish</button>
          <button className="btn btn-ghost" onClick={() => act("/close", "Closed & analysis ready")}>Close</button>
          <button className="btn btn-ghost" onClick={() => act("/archive", "Archived")}>Archive</button>
          <button className="btn btn-ghost" onClick={() => act("/duplicate", "Duplicated")}>Duplicate</button>
          <button className="btn btn-ghost" onClick={() => act("/remind", "Reminders queued")}>Remind pending</button>
          {campaign.mode === "poll" && (
            <button className="btn btn-accent" onClick={() => act("/analyze", "AI/theme analysis refreshed")}>Run analysis</button>
          )}
          {campaign.mode === "grade" && (
            <button className="btn btn-ghost" onClick={() => act("/reopen-grade", "Grade reopened")}>Reopen grade</button>
          )}
          <button className="btn btn-primary" onClick={() => downloadAuth(`/api/campaigns/${id}/export/pdf`, `campaign_${id}.pdf`)}>PDF</button>
          <button className="btn btn-primary" onClick={() => downloadAuth(`/api/campaigns/${id}/export/xlsx`, `campaign_${id}.xlsx`)}>Excel</button>
        </div>
      )}

      {poll && (
        <>
          <div className="grid-3" style={{ marginBottom: 12 }}>
            <div className="panel stat"><h3>Average /10</h3><p>{poll.average_score ?? "—"}</p></div>
            <div className="panel stat"><h3>Response rate</h3><p>{poll.response_rate}%</p></div>
            <div className="panel stat"><h3>Stars (derived)</h3><p>{poll.star_average ?? "—"}</p></div>
          </div>
          <div className="panel" style={{ marginBottom: 12, height: 280 }}>
            <h3 style={{ marginTop: 0 }}>Score distribution</h3>
            <ResponsiveContainer width="100%" height="85%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="score" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="votes" fill="#0f4c5c" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="panel" style={{ marginBottom: 12 }}>
            <h3 style={{ marginTop: 0 }}>Comment analysis</h3>
            <p>{poll.ai_summary || "No summary yet. Close campaign or run analysis."}</p>
            {poll.theme_summary && (
              <div className="grid-3">
                <div>
                  <strong>Strengths</strong>
                  <ul>{(poll.theme_summary.strengths || []).map((x: string) => <li key={x}>{x}</li>)}</ul>
                </div>
                <div>
                  <strong>Improvement areas</strong>
                  <ul>{(poll.theme_summary.improvement_areas || []).map((x: string) => <li key={x}>{x}</li>)}</ul>
                </div>
                <div>
                  <strong>Recurring topics</strong>
                  <ul>{(poll.theme_summary.recurring_topics || []).slice(0, 6).map((x: string) => <li key={x}>{x}</li>)}</ul>
                </div>
              </div>
            )}
          </div>
          <div className="panel" style={{ marginBottom: 12 }}>
            <h3 style={{ marginTop: 0 }}>Source comments ({poll.comment_count})</h3>
            {poll.comments.map((c, i) => (
              <div key={i} style={{ padding: "0.6rem 0", borderBottom: "1px solid var(--line)" }}>
                <strong>Score {c.score}</strong>
                {c.respondent_name ? ` — ${c.respondent_name}` : " — anonymous"}
                <div>{c.comment || <span className="muted">No comment</span>}</div>
              </div>
            ))}
          </div>
          {trends.length > 0 && (
            <div className="panel" style={{ marginBottom: 12 }}>
              <h3 style={{ marginTop: 0 }}>Leader trend across campaigns</h3>
              <table className="table">
                <thead><tr><th>Campaign</th><th>Average</th><th>Responses</th><th>Date</th></tr></thead>
                <tbody>
                  {trends.map((t) => (
                    <tr key={t.campaign_id}>
                      <td>{t.campaign_name}</td>
                      <td>{t.average_score?.toFixed?.(2) ?? t.average_score}</td>
                      <td>{t.response_count}</td>
                      <td>{new Date(t.captured_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {grade && (
        <div className="panel" style={{ marginBottom: 12 }}>
          <h3 style={{ marginTop: 0 }}>
            Ranking {grade.is_final ? "(final)" : "(in progress)"} — {grade.ranked_count}/{grade.total_required}
          </h3>
          <table className="table">
            <thead><tr><th>Rank</th><th>Employee</th></tr></thead>
            <tbody>
              {grade.ranking.map((r, i) => (
                <tr key={i}>
                  <td>{r.rank ?? "—"}</td>
                  <td>{r.employee_name}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {pending && (
        <div className="panel">
          <h3 style={{ marginTop: 0 }}>Pending participation (names only — answers hidden)</h3>
          <p className="muted">{pending.pending_count} pending</p>
          <ul>
            {(pending.pending || []).map((p: any) => (
              <li key={p.user_id}>{p.full_name} ({p.email})</li>
            ))}
          </ul>
        </div>
      )}
    </AppShell>
  );
}
