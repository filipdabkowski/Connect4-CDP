import { api } from "./client";

export type LoginPayload = { username: string; password: string };
export type RegisterPayload = { username: string; password: string };

export type User = {
  id: string | number;
  username?: string;
};

export type AuthResponse = {
  access_token: string;
  user?: User | null;
};

export async function registerRequest(payload: RegisterPayload): Promise<AuthResponse> {
  const res = await api.post<AuthResponse>("/auth/register", payload);
  return res.data;
}

export async function loginRequest(payload: LoginPayload): Promise<AuthResponse> {
  const res = await api.post<AuthResponse>("/auth/login", payload);
  return res.data;
}
