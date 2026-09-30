const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export type User = {
  id: number;
  email: string;
  full_name: string;
  role: string;
  department_id?: number | null;
  employee_code?: string | null;
  is_active: boolean;
  is_leader: boolean;
  locale: string;
};

export type Campaign = {
  id: number;
  name: string;
  mode: "poll" | "grade";
  status: string;
  department_id?: number | null;
  target_user_id?: number | null;
  group_head_id?: number | null;
  identity_mode: string;
  comment_rule: string;
  rank_direction: string;
  result_visibility: string;
  allow_employee_results: boolean;
  start_at?: string | null;
  end_at?: string | null;
  reminder_enabled: boolean;
  locked_settings: boolean;
  participant_count: number;
  submitted_count: number;
  target_name?: string | null;
  group_head_name?: string | null;
  department_name?: string | null;
  created_at: string;
};

function token(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("lf_token");
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers || {});
  const t = token();
  if (t) headers.set("Authorization", `Bearer ${t}`);
  if (!(options.body instanceof FormData) && options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = "Request failed";
    try {
      const data = await res.json();
      detail = data.detail || JSON.stringify(data);
    } catch {
      detail = await res.text();
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return undefined as T;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res as unknown as T;
}

export async function login(email: string, password: string) {
  const body = new URLSearchParams();
  body.set("username", email);
  body.set("password", password);
  const res = await fetch(`${API_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Login failed");
  }
  return res.json() as Promise<{ access_token: string; user: User }>;
}

export async function ssoDevLogin(email: string) {
  return api<{ access_token: string; user: User }>(
    `/api/auth/sso/dev-login?email=${encodeURIComponent(email)}`,
    { method: "POST" },
  );
}

export function downloadUrl(path: string) {
  const t = token();
  return `${API_URL}${path}${path.includes("?") ? "&" : "?"}access_token=${t || ""}`;
}

export async function downloadAuth(path: string, filename: string) {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { Authorization: `Bearer ${token()}` },
  });
  if (!res.ok) throw new Error("Download failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export { API_URL };
