"use client";

import { FormEvent, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function PollPage() {
  const { id } = useParams();
  const campaignId = Number(id);
  const { user } = useAuth();
  const router = useRouter();
  const [meta, setMeta] = useState<any>(null);
  const [score, setScore] = useState<number | null>(null);
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!user) return;
    api(`/api/campaigns/${campaignId}/poll/mine`)
      .then((m: any) => {
        setMeta(m);
        if (m.has_submitted && !m.can_edit) setDone(true);
      })
      .catch((e) => setError(e.message));
  }, [user, campaignId]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!score) {
      setError("Select a score from 1 to 10");
      return;
    }
    setError("");
    try {
      await api(`/api/campaigns/${campaignId}/poll`, {
        method: "POST",
        body: JSON.stringify({ score, comment: comment || null }),
      });
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submit failed");
    }
  }

  return (
    <AppShell>
      <h1 style={{ fontFamily: "var(--font-display)", color: "var(--teal-deep)" }}>Poll + Comment</h1>
      {!meta ? (
        <div className="panel">{error || "Loading…"}</div>
      ) : (
        <div className="panel" style={{ maxWidth: 640 }}>
          <p>
            Reviewing: <strong>{meta.target_name}</strong>
          </p>
          <p className="muted">
            Status: {meta.status} · Closes: {meta.end_at ? new Date(meta.end_at).toLocaleString() : "—"}
          </p>
          <p className="muted">
            Identity:{" "}
            {meta.identity_mode === "named"
              ? "Your name will be visible with your response."
              : meta.identity_mode === "strict_anonymous"
                ? "Your submitted answer cannot be linked back to your name in normal result access."
                : "Your name will not appear in the result report."}
          </p>
          {error && <div className="error">{error}</div>}
          {done ? (
            <div>
              <p>Thank you — your response is recorded. One response per campaign.</p>
              <button className="btn btn-ghost" onClick={() => router.push("/tasks")}>
                Back to tasks
              </button>
            </div>
          ) : (
            <form onSubmit={onSubmit}>
              <label style={{ display: "block", marginBottom: 8 }}>Score (1–10)</label>
              <div className="score-grid" style={{ marginBottom: 16 }}>
                {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
                  <button
                    type="button"
                    key={n}
                    className={`score-btn ${score === n ? "active" : ""}`}
                    onClick={() => setScore(n)}
                  >
                    {n}
                  </button>
                ))}
              </div>
              {meta.comment_rule !== "disabled" && (
                <div className="field">
                  <label>
                    Comment {meta.comment_rule === "required" ? "(required)" : "(optional)"}
                  </label>
                  <textarea rows={5} value={comment} onChange={(e) => setComment(e.target.value)} />
                </div>
              )}
              <button className="btn btn-primary" type="submit">
                Review & submit
              </button>
            </form>
          )}
        </div>
      )}
    </AppShell>
  );
}
