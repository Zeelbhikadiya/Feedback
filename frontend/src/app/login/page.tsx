"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const { login, loginSso, user } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("hr@company.local");
  const [password, setPassword] = useState("Password123!");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) {
    router.replace("/dashboard");
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  async function onSso() {
    setBusy(true);
    setError("");
    try {
      await loginSso(email);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "SSO failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="panel login-card">
        <h1>LeaderPulse</h1>
        <p>Campaign-based leader feedback, polls and unique ranking.</p>
        {error && <div className="error">{error}</div>}
        <form onSubmit={onSubmit}>
          <div className="field">
            <label>Email</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
          </div>
          <div className="field">
            <label>Password</label>
            <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required />
          </div>
          <button className="btn btn-primary" style={{ width: "100%" }} disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <button className="btn btn-ghost" style={{ width: "100%", marginTop: 10 }} onClick={onSso} disabled={busy}>
          Continue with company SSO (dev)
        </button>
        <p className="muted" style={{ marginTop: 16 }}>
          Demo: hr@company.local / e1@company.local / grouphead@company.local — Password123!
        </p>
      </div>
    </div>
  );
}
