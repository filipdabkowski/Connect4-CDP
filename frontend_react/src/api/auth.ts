import { api } from "./client";

export type User = {
  username: string;
  games_played: number;
};

export type LoginPayload = {
    username: string;
    password: string;
}

export type LoginResponse = {
  access: string;
  refresh: string;
};

export async function login(payload: LoginPayload): Promise<LoginResponse> {
  const res = await api.post<LoginResponse>("/auth/login", payload);
  return res.data;
}

export async function getMe(): Promise<User> {
    const res = await api.get<User>("player/");
    return res.data;
}
