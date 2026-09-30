"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { isManager, useAuth } from "@/lib/auth";
import { Locale, t } from "@/lib/i18n";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading, logout, setLocale } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const locale = (user?.locale as Locale) || "en";

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div className="login-wrap">
        <div className="panel">Loading…</div>
      </div>
    );
  }

  const links = [
    { href: "/dashboard", label: t(locale, "dashboard"), show: true },
    { href: "/campaigns", label: t(locale, "campaigns"), show: true },
    { href: "/tasks", label: t(locale, "myTasks"), show: true },
    { href: "/people", label: t(locale, "people"), show: isManager(user.role) },
    { href: "/audit", label: t(locale, "audit"), show: isManager(user.role) },
  ];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          {t(locale, "brand")}
          <small>{t(locale, "tagline")}</small>
        </div>
        <nav className="nav">
          {links
            .filter((l) => l.show)
            .map((l) => (
              <Link key={l.href} href={l.href} className={pathname.startsWith(l.href) ? "active" : ""}>
                {l.label}
              </Link>
            ))}
        </nav>
        <div style={{ marginTop: "auto" }}>
          <div className="muted" style={{ color: "#d7e8ec", marginBottom: 8 }}>
            {user.full_name}
            <br />
            <span style={{ opacity: 0.75 }}>{user.role.replace("_", " ")}</span>
          </div>
          <label className="muted" style={{ color: "#d7e8ec", display: "block", marginBottom: 6 }}>
            {t(locale, "language")}
          </label>
          <select
            value={locale}
            onChange={(e) => setLocale(e.target.value)}
            style={{ width: "100%", marginBottom: 10, borderRadius: 8, padding: "0.45rem" }}
          >
            <option value="en">English</option>
            <option value="gu">Gujarati</option>
            <option value="hi">Hindi</option>
          </select>
          <button className="btn btn-ghost" style={{ width: "100%", color: "white", borderColor: "rgba(255,255,255,0.25)" }} onClick={logout}>
            {t(locale, "logout")}
          </button>
        </div>
      </aside>
      <main className="main fade-in">{children}</main>
    </div>
  );
}
