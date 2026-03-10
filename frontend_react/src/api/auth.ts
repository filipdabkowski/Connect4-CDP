import { api } from "./client";
import axios from "axios";

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

export type RegisterPayload = {
    username: string;
    password: string;
}

export type RegisterResponse = {
    username: string;
}

export type FieldErrors = Record<string, string[]>;

export class ApiValidationError extends Error {
    fieldErrors: FieldErrors;

    constructor(fieldErrors: FieldErrors) {
        super("Validation failed");
        this.name = "ApiValidationError";
        this.fieldErrors = fieldErrors;
    }
}

export async function login(payload: LoginPayload): Promise<LoginResponse> {
  const res = await api.post<LoginResponse>("/auth/login", payload);
  return res.data;
}

export async function getMe(): Promise<User> {
    const res = await api.get<User>("player/");
    return res.data;
}

export async function register(payload: RegisterPayload): Promise<RegisterResponse> {
    try {
        const res = await api.post("/auth/register", payload);
        return res.data;
    } catch (err: unknown) {
        if (axios.isAxiosError(err) && err.response?.data) {
            const data = err.response.data;

            // { username: ["..."], password: ["..."] }
            if (typeof data === "object" && data !== null) {
                throw new ApiValidationError(data as FieldErrors);
            }
        }

        throw new Error("Registration failed");
    }
}
