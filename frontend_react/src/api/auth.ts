import {api} from "./client";
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

export type RefreshPayload = {
    refresh: string;
};

export type RefreshResponse = {
    access: string;
};

export type RegisterPayload = {
    username: string;
    password: string;
}

export type RegisterResponse = {
    username: string;
}

export type FieldErrors = Record<string, string[]>;

/**
 * Represents field-level validation errors returned by the API.
 *
 * @param fieldErrors - A map of field names to user-facing error messages.
 * @returns An Error instance carrying the parsed field errors.
 */
export class ApiValidationError extends Error {
    fieldErrors: FieldErrors;

    constructor(fieldErrors: FieldErrors) {
        super("Validation failed");
        this.name = "ApiValidationError";
        this.fieldErrors = fieldErrors;
    }
}

/**
 * Authenticate a user and return JWT tokens.
 *
 * @param payload - Username and password submitted from the login form.
 * @returns Access and refresh tokens from the backend.
 */
export async function login(payload: LoginPayload): Promise<LoginResponse> {
    try {
        const res = await api.post<LoginResponse>("/auth/login", payload);
        return res.data;
    } catch (err: unknown) {
        if (axios.isAxiosError(err) && err.response?.data) {
            const data = err.response.data;
            if (typeof data === "object" && data !== null) {
                throw new ApiValidationError(data as FieldErrors);
            }
        }
        
        throw new Error("Login failed.")
    }
}

/**
 * Fetch the profile for the current authenticated player.
 *
 * @returns The current user's player profile.
 */
export async function getMe(): Promise<User> {
    const res = await api.get<User>("player/");
    return res.data;
}

/**
 * Exchange a refresh token for a new access token.
 *
 * @param payload - Refresh token currently stored by the client.
 * @returns A replacement access token.
 */
export async function refreshAccessToken(payload: RefreshPayload): Promise<RefreshResponse> {
    const res = await api.post<RefreshResponse>("/auth/refresh", payload);
    return res.data;
}

/**
 * Register a new player account.
 *
 * @param payload - Username and password from the registration form.
 * @returns The created account summary from the backend.
 */
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

        throw new Error("Registration failed.");
    }
}
