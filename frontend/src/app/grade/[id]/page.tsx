"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Emp = { id: number; full_name: string };
type RankRow = { employee_id: number; rank: number | null };

export default function GradePage() {
  const { id } = useParams();
  const campaignId = Number(id);
  const { user } = useAuth();
  const [data, setData] = useState<any>(null);
  const [ranks, setRanks] = useState<Record<number, number | "">>({});
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");

  async function load() {
    const d = await api(`/api/campaigns/${campaignId}/grade`);
    setData(d);
    const map: Record<number, number | ""> = {};
    for (const r of d.ranking || []) {
      map[r.employee_id] = r.rank ?? "";
    }
    setRanks(map);
  }

  useEffect(() => {
    if (user) load().catch((e) => setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, campaignId]);

  const used = useMemo(() => {
    return new Set(Object.values(ranks).filter((v) => v !== "" && v != null) as number[]);
  }, [ranks]);

  const n = data?.total_required || 0;
  const allRanks = Array.from({ length: n }, (_, i) => i + 1);

  function setRank(employeeId: number, value: string) {
    setRanks((prev) => ({ ...prev, [employeeId]: value === "" ? "" : Number(value) }));
  }

  async function save(finalize: boolean) {
    setError("");
    setMsg("");
    const payload = Object.entries(ranks)
      .filter(([, rank]) => rank !== "")
      .map(([employee_id, rank]) => ({ employee_id: Number(employee_id), rank: Number(rank) }));
    try {
      const res = await api(`/api/campaigns/${campaignId}/grade`, {
        method: "POST",
        body: JSON.stringify({ ranks: payload, finalize }),
      });
      setData((d: any) => ({ ...d, ...res }));
      setMsg(finalize ? "Final ranking submitted and locked." : "Draft saved.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    }
  }

  if (!data) {
    return (
      <AppShell>
        <div className="panel">{error || "Loading…"}</div>
      </AppShell>
    );
  }

  const progress = Object.values(ranks).filter((v) => v !== "").length;

  return (
    <AppShell>
      <h1 style={{ fontFamily: "var(--font-display)", color: "var(--teal-deep)" }}>Grade / Unique Ranking</h1>
      <div className="panel" style={{ marginBottom: 12 }}>
        <p>
          <strong>{data.rank_direction_label}</strong>
        </p>
        <p className="muted">
          Progress: {progress} of {n} ranked · Available ranks:{" "}
          {allRanks.filter((r) => !used.has(r)).join(", ") || "none"}
        </p>
        {error && <div className="error">{error}</div>}
        {msg && <p style={{ color: "var(--ok)" }}>{msg}</p>}
      </div>

      <div className="panel" style={{ marginBottom: 12 }}>
        <table className="table">
          <thead>
            <tr>
              <th>Employee</th>
              <th>Assigned rank</th>
            </tr>
          </thead>
          <tbody>
            {(data.employees as Emp[]).map((emp) => {
              const current = ranks[emp.id];
              return (
                <tr key={emp.id}>
                  <td>{emp.full_name}</td>
                  <td>
                    <select
                      disabled={data.is_final}
                      value={current === undefined || current === null ? "" : String(current)}
                      onChange={(e) => setRank(emp.id, e.target.value)}
                    >
                      <option value="">Select rank…</option>
                      {allRanks.map((r) => {
                        const taken = used.has(r) && current !== r;
                        return (
                          <option key={r} value={r} disabled={taken}>
                            {r}
                            {taken ? " (used)" : ""}
                          </option>
                        );
                      })}
                    </select>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {!data.is_final && (
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn btn-ghost" onClick={() => save(false)}>
            Save draft
          </button>
          <button className="btn btn-primary" onClick={() => save(true)}>
            Review & final submit
          </button>
        </div>
      )}

      {data.is_final && (
        <div className="panel">
          <h3>Final order</h3>
          <ol>
            {[...(data.ranking as RankRow[])]
              .filter((r) => r.rank != null)
              .sort((a: any, b: any) => a.rank - b.rank)
              .map((r: any) => (
                <li key={r.employee_id}>
                  #{r.rank} — {r.employee_name}
                </li>
              ))}
          </ol>
        </div>
      )}
    </AppShell>
  );
}
