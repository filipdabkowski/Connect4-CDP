import React, { createContext, useContext, useMemo, useState } from "react";
import type { User, RegisterPayload } from "../api/auth";
import { loginRequest, registerRequest } from "../api/auth";

type AuthContextValue = {
  user: User | null;
  isAuthed: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    const raw = localStorage.getItem("user");
    return raw ? (JSON.parse(raw) as User) : null;
  });

  const isAuthed = !!localStorage.getItem("access_token");

  async function login(username: string, password: string) {
    const data = await loginRequest({ username, password });
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("user", JSON.stringify(data.user ?? null));
    setUser(data.user ?? null);
  }

  async function register(payload: RegisterPayload) {
    const data = await registerRequest(payload);
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("user", JSON.stringify(data.user ?? null));
    setUser(data.user ?? null);
  }

  function logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
    setUser(null);
  }

  const value = useMemo(
    () => ({ user, isAuthed, login, register, logout }),
    [user, isAuthed]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
