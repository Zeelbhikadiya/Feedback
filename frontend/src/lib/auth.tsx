"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { User, api, login as apiLogin, ssoDevLogin } from "./api";

type AuthState = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  loginSso: (email: string) => Promise<void>;
  logout: () => void;
  setLocale: (locale: string) => void;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const t = localStorage.getItem("lf_token");
    if (!t) {
      setLoading(false);
      return;
    }
    api<User>("/api/auth/me")
      .then(setUser)
      .catch(() => localStorage.removeItem("lf_token"))
      .finally(() => setLoading(false));
  }, []);

  async function login(email: string, password: string) {
    const data = await apiLogin(email, password);
    localStorage.setItem("lf_token", data.access_token);
    setUser(data.user);
  }

  async function loginSso(email: string) {
    const data = await ssoDevLogin(email);
    localStorage.setItem("lf_token", data.access_token);
    setUser(data.user);
  }

  function logout() {
    localStorage.removeItem("lf_token");
    setUser(null);
  }

  function setLocale(locale: string) {
    if (!user) return;
    localStorage.setItem("lf_locale", locale);
    setUser({ ...user, locale });
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, loginSso, logout, setLocale }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside provider");
  return ctx;
}

export function isManager(role?: string) {
  return role === "system_admin" || role === "management";
}
