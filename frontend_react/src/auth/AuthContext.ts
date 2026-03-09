import type {LoginPayload, RegisterPayload, User} from "../api/auth.ts";
import { createContext } from "react";

export type AuthContextType = {
    user: User | null;
    isAuth: boolean;
    login: (data: LoginPayload) => Promise<void>;
    logout: () => Promise<void>;
    register: (data: RegisterPayload) => Promise<void>;
};

export const AuthContext = createContext<AuthContextType | null>(null);
